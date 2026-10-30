import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// Per-capture status shown in the sync queue.
/// draft -> queued -> submitted (server is checking) -> accepted | flagged | rejected.
/// `failed` means the app gave up on a retry (e.g. a 409); the reason says why.
class CaptureStatus {
  /// Taken and signed, but not saved from the review step yet. Never uploaded.
  static const draft = 'draft';
  static const queued = 'queued';
  static const submitted = 'submitted';
  static const accepted = 'accepted';
  static const flagged = 'flagged';
  static const rejected = 'rejected';
  static const failed = 'failed';
  static const open = {queued, submitted};
}

class QueuedCapture {
  QueuedCapture({
    required this.id,
    required this.projectId,
    this.milestoneId,
    required this.kind,
    required this.filePath,
    required this.sha256,
    required this.capturedAt,
    required this.gpsTime,
    required this.lat,
    required this.lon,
    required this.accuracyM,
    required this.deviceId,
    required this.signature,
    this.status = CaptureStatus.queued,
    this.reason,
    this.storageKey,
    this.evidenceId,
    this.attempts = 0,
    this.nextTry = 0,
    this.note,
    this.checklistItem,
    this.contextRef,
    this.asContractor = false,
  });

  final String id; // client UUID, also the Idempotency-Key base
  final String projectId;
  final String? milestoneId;
  final String kind; // photo | video
  final String filePath;
  final String sha256;
  final DateTime capturedAt;
  final DateTime gpsTime;
  final double lat;
  final double lon;
  final double accuracyM;
  final String deviceId;
  final String signature;
  final String status;
  final String? reason;
  final String? storageKey;
  final String? evidenceId;
  final int attempts;
  final int nextTry; // epoch ms

  /// Kept on the phone only (the evidence API has no note field): the supervisor's note, the
  /// checklist item the photo supports, and what it belongs to (spot_check:id).
  final String? note;
  final String? checklistItem;
  final String? contextRef;
  final bool asContractor;

  Map<String, Object?> toRow() => {
        'id': id,
        'project_id': projectId,
        'milestone_id': milestoneId,
        'kind': kind,
        'file_path': filePath,
        'sha256': sha256,
        'captured_at': capturedAt.toUtc().millisecondsSinceEpoch,
        'gps_time': gpsTime.toUtc().millisecondsSinceEpoch,
        'lat': lat,
        'lon': lon,
        'accuracy_m': accuracyM,
        'device_id': deviceId,
        'signature': signature,
        'status': status,
        'reason': reason,
        'storage_key': storageKey,
        'evidence_id': evidenceId,
        'attempts': attempts,
        'next_try': nextTry,
        'note': note,
        'checklist_item': checklistItem,
        'context_ref': contextRef,
        'as_contractor': asContractor ? 1 : 0,
      };

  factory QueuedCapture.fromRow(Map<String, Object?> r) => QueuedCapture(
        id: r['id'] as String,
        projectId: r['project_id'] as String,
        milestoneId: r['milestone_id'] as String?,
        kind: r['kind'] as String,
        filePath: r['file_path'] as String,
        sha256: r['sha256'] as String,
        capturedAt: DateTime.fromMillisecondsSinceEpoch(r['captured_at'] as int, isUtc: true),
        gpsTime: DateTime.fromMillisecondsSinceEpoch(r['gps_time'] as int, isUtc: true),
        lat: (r['lat'] as num).toDouble(),
        lon: (r['lon'] as num).toDouble(),
        accuracyM: (r['accuracy_m'] as num).toDouble(),
        deviceId: r['device_id'] as String,
        signature: r['signature'] as String,
        status: r['status'] as String,
        reason: r['reason'] as String?,
        storageKey: r['storage_key'] as String?,
        evidenceId: r['evidence_id'] as String?,
        attempts: r['attempts'] as int,
        nextTry: r['next_try'] as int,
        note: r['note'] as String?,
        checklistItem: r['checklist_item'] as String?,
        contextRef: r['context_ref'] as String?,
        asContractor: (r['as_contractor'] as int? ?? 0) == 1,
      );

  /// Time left of the server's 72 h upload window.
  Duration get windowLeft => const Duration(hours: 72) - DateTime.now().toUtc().difference(capturedAt);

  /// True from 48 h after the shutter: the app warns the supervisor to get a signal.
  bool get uploadDueSoon => windowLeft < const Duration(hours: 24);
}

/// Local store for captures waiting to upload. Photos live in the app's private folder.
///
/// Not yet encrypted at rest (the roadmap asks for an encrypted DB); the files are in the app's
/// sandbox and everything on them is signed, so tampering is caught by the server.
class QueueDb {
  QueueDb._(this._db);
  final Database _db;

  static Future<QueueDb> open({String? path}) async {
    final file = path ?? p.join(await getDatabasesPath(), 'captures.db');
    final db = await openDatabase(
      file,
      version: 3,
      onCreate: (db, _) async {
        await db.execute('''
          CREATE TABLE captures (
            id TEXT PRIMARY KEY, project_id TEXT NOT NULL, milestone_id TEXT, kind TEXT NOT NULL,
            file_path TEXT NOT NULL, sha256 TEXT NOT NULL, captured_at INTEGER NOT NULL,
            gps_time INTEGER NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, accuracy_m REAL NOT NULL,
            device_id TEXT NOT NULL, signature TEXT NOT NULL, status TEXT NOT NULL, reason TEXT,
            storage_key TEXT, evidence_id TEXT, attempts INTEGER NOT NULL DEFAULT 0,
            next_try INTEGER NOT NULL DEFAULT 0, note TEXT, checklist_item TEXT, context_ref TEXT,
            as_contractor INTEGER NOT NULL DEFAULT 0)''');
        await _createActions(db);
      },
      onUpgrade: (db, from, _) async {
        if (from < 2) {
          await db.execute('ALTER TABLE captures ADD COLUMN note TEXT');
          await db.execute('ALTER TABLE captures ADD COLUMN checklist_item TEXT');
          await db.execute('ALTER TABLE captures ADD COLUMN context_ref TEXT');
          await db.execute('ALTER TABLE captures ADD COLUMN as_contractor INTEGER NOT NULL DEFAULT 0');
        }
        if (from < 3) await _createActions(db);
      },
    );
    return QueueDb._(db);
  }

  static Future<void> _createActions(Database db) => db.execute('''
        CREATE TABLE IF NOT EXISTS actions (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL, path TEXT NOT NULL, body TEXT NOT NULL,
          project_id TEXT, label TEXT NOT NULL, status TEXT NOT NULL, reason TEXT,
          attempts INTEGER NOT NULL DEFAULT 0, next_try INTEGER NOT NULL DEFAULT 0,
          created_at INTEGER NOT NULL)''');

  Future<void> insert(QueuedCapture c) => _db.insert('captures', c.toRow());

  Future<QueuedCapture?> byId(String id) async {
    final rows = await _db.query('captures', where: 'id = ?', whereArgs: [id]);
    return rows.isEmpty ? null : QueuedCapture.fromRow(rows.first);
  }

  Future<List<QueuedCapture>> all({String? projectId}) async {
    final rows = await _db.query('captures',
        where: projectId == null ? null : 'project_id = ?',
        whereArgs: projectId == null ? null : [projectId],
        orderBy: 'captured_at DESC');
    return rows.map(QueuedCapture.fromRow).toList();
  }

  /// Oldest first, ready to retry now. Drafts are never uploaded.
  Future<List<QueuedCapture>> due(int nowMs) async {
    final rows = await _db.query('captures',
        where: "status = 'queued' AND next_try <= ?", whereArgs: [nowMs], orderBy: 'captured_at ASC');
    return rows.map(QueuedCapture.fromRow).toList();
  }

  Future<List<QueuedCapture>> submitted() async => (await _db.query('captures',
          where: "status = 'submitted'", orderBy: 'captured_at ASC'))
      .map(QueuedCapture.fromRow)
      .toList();

  Future<int> unsentCount() async => Sqflite.firstIntValue(await _db.rawQuery(
          "SELECT COUNT(*) FROM captures WHERE status IN ('queued', 'draft')")) ??
      0;

  Future<void> update(String id, Map<String, Object?> values) =>
      _db.update('captures', values, where: 'id = ?', whereArgs: [id]);

  /// A draft the supervisor kept: from now on it uploads like any other capture.
  Future<void> save(String id, {String? note, String? checklistItem}) => update(id, {
        'status': CaptureStatus.queued,
        'note': (note?.trim().isEmpty ?? true) ? null : note!.trim(),
        'checklist_item': checklistItem,
      });

  /// A draft left behind (the app was closed in the review step) is kept, not lost.
  Future<void> promoteDrafts() =>
      _db.update('captures', {'status': CaptureStatus.queued}, where: "status = 'draft'");

  /// Retake: remove the row and its file.
  Future<void> discard(QueuedCapture c) async {
    await _db.delete('captures', where: 'id = ?', whereArgs: [c.id]);
    final f = File(c.filePath);
    if (await f.exists()) await f.delete();
  }

  // --- queued writes (claim and verify made without a signal) -------------------------------

  Future<void> addAction(QueuedAction a) => _db.insert('actions', a.toRow());

  Future<List<QueuedAction>> actions({bool openOnly = false}) async => (await _db.query('actions',
          where: openOnly ? "status = 'queued'" : null, orderBy: 'created_at ASC'))
      .map(QueuedAction.fromRow)
      .toList();

  Future<void> updateAction(String id, Map<String, Object?> values) =>
      _db.update('actions', values, where: 'id = ?', whereArgs: [id]);

  Future<void> deleteAction(String id) => _db.delete('actions', where: 'id = ?', whereArgs: [id]);

  Future<void> close() => _db.close();
}

/// A write the supervisor or contractor made offline (claim, verify), sent later with the same
/// `Idempotency-Key` (its id), after the evidence it depends on has been accepted.
class QueuedAction {
  QueuedAction({
    required this.id,
    required this.kind,
    required this.path,
    required this.body,
    this.projectId,
    required this.label,
    this.status = 'queued',
    this.reason,
    this.attempts = 0,
    this.nextTry = 0,
    int? createdAt,
  }) : createdAt = createdAt ?? DateTime.now().millisecondsSinceEpoch;

  final String id;
  final String kind; // claim | verify
  final String path;
  final String body; // JSON
  final String? projectId;
  final String label;
  final String status; // queued | done | failed
  final String? reason;
  final int attempts;
  final int nextTry;
  final int createdAt;

  Map<String, Object?> toRow() => {
        'id': id,
        'kind': kind,
        'path': path,
        'body': body,
        'project_id': projectId,
        'label': label,
        'status': status,
        'reason': reason,
        'attempts': attempts,
        'next_try': nextTry,
        'created_at': createdAt,
      };

  factory QueuedAction.fromRow(Map<String, Object?> r) => QueuedAction(
        id: r['id'] as String,
        kind: r['kind'] as String,
        path: r['path'] as String,
        body: r['body'] as String,
        projectId: r['project_id'] as String?,
        label: r['label'] as String,
        status: r['status'] as String,
        reason: r['reason'] as String?,
        attempts: r['attempts'] as int,
        nextTry: r['next_try'] as int,
        createdAt: r['created_at'] as int,
      );
}
