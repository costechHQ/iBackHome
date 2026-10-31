import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import 'api.dart';
import 'api_error.dart';
import 'queue_db.dart';

/// Uploads queued captures, oldest first, and follows their server checks.
///
/// Each capture goes: `POST /evidence/upload-url` -> `PUT` the file -> `POST /evidence`.
/// The capture's own UUID is the `Idempotency-Key`, so a retry after a lost answer never makes
/// a duplicate. Failures wait 5 s, 10 s, 20 s ... up to 10 minutes before the next try.
class SyncService extends ChangeNotifier {
  SyncService(this._api, this._db, {Dio? uploader}) : _uploader = uploader ?? Dio();

  final Api _api;
  final QueueDb _db;
  final Dio _uploader; // no auth header: the URL is pre-signed storage
  StreamSubscription<List<ConnectivityResult>>? _net;
  Timer? _timer;
  bool _running = false;

  bool get running => _running;

  bool _online = true;

  /// False while the phone reports no network. The sync strip and the offline banner read this.
  bool get online => _online;

  DateTime? _lastSyncedAt;

  /// When a sync run last finished while online (shown as "synced 08:32").
  DateTime? get lastSyncedAt => _lastSyncedAt;

  void _setOnline(List<ConnectivityResult> r) {
    final now = r.any((c) => c != ConnectivityResult.none);
    if (now != _online) {
      _online = now;
      notifyListeners();
    }
  }

  void start() {
    unawaited(Connectivity().checkConnectivity().then(_setOnline));
    _net = Connectivity().onConnectivityChanged.listen((r) {
      _setOnline(r);
      if (_online) unawaited(syncNow());
    });
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => unawaited(syncNow()));
    unawaited(syncNow());
  }

  @override
  void dispose() {
    _net?.cancel();
    _timer?.cancel();
    super.dispose();
  }

  static int backoffMs(int attempts) =>
      math.min(const Duration(minutes: 10).inMilliseconds, 5000 * math.pow(2, attempts).toInt());

  /// Never throws; progress is saved per capture.
  Future<void> syncNow({bool force = false}) async {
    if (_running || _api.tokens.accessToken == null) return; // nothing to send until signed in
    _running = true;
    notifyListeners();
    try {
      final due = await _db.due(force ? 1 << 62 : DateTime.now().millisecondsSinceEpoch);
      for (final c in due) {
        if (!await _upload(c)) break; // offline or server busy: keep order, try again later
      }
      await _refreshStatuses();
      await _sendActions();
      if (_online) _lastSyncedAt = DateTime.now();
    } finally {
      _running = false;
      notifyListeners();
    }
  }

  /// True to carry on with the next capture.
  Future<bool> _upload(QueuedCapture c) async {
    try {
      var key = c.storageKey;
      if (key == null) {
        final slot = await _api.post<Map<String, dynamic>>(
          '/evidence/upload-url',
          body: {
            'project_id': c.projectId,
            'kind': c.kind,
            'content_type': c.kind == 'photo' ? 'image/jpeg' : 'video/mp4',
          },
          idempotencyKey: '${c.id}-u${c.attempts}', // a new URL if the last one expired
        );
        final file = File(c.filePath);
        await _uploader.put<void>(
          slot['upload_url'] as String,
          data: file.openRead(),
          options: Options(
            method: slot['method'] as String? ?? 'PUT',
            headers: {
              ...(slot['headers'] as Map).cast<String, String>(),
              Headers.contentLengthHeader: await file.length(),
            },
          ),
        );
        key = slot['storage_key'] as String;
        await _db.update(c.id, {'storage_key': key});
      }
      final out = await _api.post<Map<String, dynamic>>(
        '/evidence',
        body: {
          'project_id': c.projectId,
          if (c.milestoneId != null) 'milestone_id': c.milestoneId,
          'kind': c.kind,
          'storage_key': key,
          'file_sha256': c.sha256,
          'captured_at': c.capturedAt.toUtc().toIso8601String(),
          'gps_time': c.gpsTime.toUtc().toIso8601String(),
          'latitude': c.lat,
          'longitude': c.lon,
          'accuracy_m': c.accuracyM,
          'device_id': c.deviceId,
          'signature': c.signature,
        },
        idempotencyKey: c.id,
      );
      await _db.update(c.id, {
        'evidence_id': out['id'],
        'status': _statusFrom(out['status'] as String?),
        'reason': out['reject_reason'],
      });
      return true;
    } on DioException catch (e) {
      // The pre-signed PUT failed. Network trouble retries; a refusal gets a fresh URL.
      await _retryLater(c, e.response == null ? null : 'Upload refused (${e.response!.statusCode}).',
          dropKey: e.response != null);
      return e.response != null;
    } on ApiError catch (e) {
      if (e.isRetryable || e.status == 401) {
        await _retryLater(c, null);
        return false;
      }
      // The server refused this capture for good (422 bad metadata, 403 revoked device, 409 ...).
      await _db.update(c.id, {
        'status': e.status == 409 ? CaptureStatus.failed : CaptureStatus.rejected,
        'reason': e.message,
      });
      return true;
    }
  }

  Future<void> _retryLater(QueuedCapture c, String? reason, {bool dropKey = false}) =>
      _db.update(c.id, {
        'attempts': c.attempts + 1,
        'next_try': DateTime.now().millisecondsSinceEpoch + backoffMs(c.attempts),
        'reason': reason,
        if (dropKey) 'storage_key': null,
      });

  /// Sends the claims and verifications made without a signal, oldest first, each with its own
  /// id as the `Idempotency-Key` so a retry never does the work twice.
  ///
  /// A verification names its photos by capture id; it waits until every one of them has been
  /// accepted by the server, then swaps in the server's evidence ids.
  Future<void> _sendActions() async {
    final now = DateTime.now().millisecondsSinceEpoch;
    for (final a in await _db.actions(openOnly: true)) {
      if (a.nextTry > now) continue;
      try {
        final body = jsonDecode(a.body) as Map<String, dynamic>;
        if (a.kind == 'verify' && body['decision'] == 'verified') {
          final resolved = await resolveChecklist(body['checklist'] as List);
          if (resolved == null) continue; // its photos are still on the way
          if (resolved.isEmpty) {
            await _db.updateAction(a.id, {
              'status': 'failed',
              'reason': 'A photo you used was rejected by the server. Capture it again and verify once more.',
            });
            continue;
          }
          body['checklist'] = resolved;
        }
        await _api.post<Map<String, dynamic>>(a.path, body: body.isEmpty ? null : body, idempotencyKey: a.id);
        await _db.updateAction(a.id, {'status': 'done', 'reason': null});
      } on ApiError catch (e) {
        if (e.isRetryable || e.status == 401) {
          await _db.updateAction(a.id, {
            'attempts': a.attempts + 1,
            'next_try': now + backoffMs(a.attempts),
          });
          if (e.isNetwork) break; // still offline: stop and try again later
        } else {
          await _db.updateAction(a.id, {
            'status': 'failed',
            'reason': e.status == 409
                ? 'This changed while you were offline, so nothing was done. ${e.message}'
                : e.message,
          });
        }
      }
    }
    notifyListeners();
  }

  /// Turns `capture_ids` into the server's `evidence_ids`. Returns null while any capture is
  /// still waiting, and an empty list when one was rejected.
  @visibleForTesting
  Future<List<Map<String, dynamic>>?> resolveChecklist(List<dynamic> checklist) async {
    final out = <Map<String, dynamic>>[];
    for (final raw in checklist) {
      final item = (raw as Map).cast<String, dynamic>();
      final ids = <String>[];
      for (final captureId in (item['capture_ids'] as List? ?? const []).cast<String>()) {
        final c = await _db.byId(captureId);
        if (c == null) continue;
        if (c.status == CaptureStatus.rejected || c.status == CaptureStatus.failed) return [];
        if (c.status != CaptureStatus.accepted || c.evidenceId == null) return null;
        ids.add(c.evidenceId!);
      }
      out.add({'item': item['item'], 'passed': item['passed'], 'evidence_ids': ids});
    }
    return out;
  }

  /// Submitted captures are checked in the background on the server; ask how they ended.
  Future<void> _refreshStatuses() async {
    final pending = await _db.submitted();
    for (final projectId in {for (final c in pending) c.projectId}) {
      try {
        final page = await _api.get<Map<String, dynamic>>(
          '/projects/$projectId/evidence',
          query: {'limit': 100},
        );
        final byId = {for (final i in (page['items'] as List)) (i as Map)['id']: i};
        for (final c in pending.where((c) => c.projectId == projectId)) {
          final item = byId[c.evidenceId];
          if (item == null) continue;
          await _db.update(c.id, {
            'status': _statusFrom(item['status'] as String?),
            'reason': item['reject_reason'],
          });
        }
      } on ApiError {
        // Try again on the next run.
      }
    }
  }

  static String _statusFrom(String? server) => switch (server) {
        'accepted' => CaptureStatus.accepted,
        'flagged' => CaptureStatus.flagged,
        'rejected' => CaptureStatus.rejected,
        _ => CaptureStatus.submitted, // pending_checks
      };
}
