import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

/// Per-capture status shown in the sync queue.
/// queued -> uploading -> submitted (server is checking) -> accepted | flagged | rejected.
/// `failed` means the app gave up on a retry (e.g. a 409); the reason says why.
class CaptureStatus {
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
  });

  final String id; // client UUID, also the Idempotency-Key base
  final String projectId;
  final String? milestoneId;
  final String kind;
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
      );

  /// Hours left of the server's 72 h upload window.
  Duration get windowLeft =>
      const Duration(hours: 72) - DateTime.now().toUtc().difference(capturedAt);
}

/// Local store for captures waiting to upload. Photos live in the app's private folder.
///
/// Not yet encrypted at rest (the roadmap asks for an encrypted DB); the files are in the app's
/// sandbox and everything on them is signed, so tampering is caught by the server.
class QueueDb {
  QueueDb._(this._db);
  final Database _db;

  static Future<QueueDb> open({String? path}) async {
    final db = await openDatabase(
      path ?? p.join(await getDatabasesPath(), 'captures.db'),
      version: 1,
      onCreate: (db, _) => db.execute('''
        CREATE TABLE captures (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL, milestone_id TEXT, kind TEXT NOT NULL,
          file_path TEXT NOT NULL, sha256 TEXT NOT NULL, captured_at INTEGER NOT NULL,
          gps_time INTEGER NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, accuracy_m REAL NOT NULL,
          device_id TEXT NOT NULL, signature TEXT NOT NULL, status TEXT NOT NULL, reason TEXT,
          storage_key TEXT, evidence_id TEXT, attempts INTEGER NOT NULL DEFAULT 0,
          next_try INTEGER NOT NULL DEFAULT 0)'''),
    );
    return QueueDb._(db);
  }

  Future<void> insert(QueuedCapture c) => _db.insert('captures', c.toRow());

  Future<List<QueuedCapture>> all({String? projectId}) async {
    final rows = await _db.query('captures',
        where: projectId == null ? null : 'project_id = ?',
        whereArgs: projectId == null ? null : [projectId],
        orderBy: 'captured_at DESC');
    return rows.map(QueuedCapture.fromRow).toList();
  }

  /// Oldest first, ready to retry now.
  Future<List<QueuedCapture>> due(int nowMs) async {
    final rows = await _db.query('captures',
        where: "status = 'queued' AND next_try <= ?", whereArgs: [nowMs], orderBy: 'captured_at ASC');
    return rows.map(QueuedCapture.fromRow).toList();
  }

  Future<List<QueuedCapture>> submitted() async => (await _db.query('captures',
          where: "status = 'submitted'", orderBy: 'captured_at ASC'))
      .map(QueuedCapture.fromRow)
      .toList();

  Future<void> update(String id, Map<String, Object?> values) =>
      _db.update('captures', values, where: 'id = ?', whereArgs: [id]);

  Future<void> delete(String id) => _db.delete('captures', where: 'id = ?', whereArgs: [id]);

  Future<void> close() => _db.close();
}
