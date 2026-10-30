import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/sync_service.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

QueuedCapture capture(String id, String status, {String? evidenceId, String? item}) => QueuedCapture(
      id: id,
      projectId: 'p1',
      milestoneId: 'm1',
      kind: 'photo',
      filePath: '/tmp/$id.jpg',
      sha256: 'a' * 64,
      capturedAt: DateTime.now().toUtc(),
      gpsTime: DateTime.now().toUtc(),
      lat: 6.45,
      lon: 7.5,
      accuracyM: 8,
      deviceId: 'd1',
      signature: 'sig',
      status: status,
      evidenceId: evidenceId,
      checklistItem: item,
    );

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;
  late QueueDb db;
  late SyncService sync;
  late Directory tmp;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_queue');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
    sync = SyncService(Api(TokenStore()), db);
  });

  tearDown(() async {
    await db.close();
    await tmp.delete(recursive: true);
  });

  group('drafts', () {
    test('a draft is not uploaded until it is saved', () async {
      await db.insert(capture('c1', CaptureStatus.draft));
      expect(await db.due(1 << 62), isEmpty);
      await db.save('c1', note: '  north wall  ', checklistItem: 'Workmanship is acceptable');
      final due = await db.due(1 << 62);
      expect(due.single.note, 'north wall');
      expect(due.single.checklistItem, 'Workmanship is acceptable');
    });

    test('drafts left behind are kept on the next launch', () async {
      await db.insert(capture('c1', CaptureStatus.draft));
      await db.promoteDrafts();
      expect((await db.due(1 << 62)).length, 1);
    });

    test('unsent count includes drafts and waiting captures only', () async {
      await db.insert(capture('c1', CaptureStatus.draft));
      await db.insert(capture('c2', CaptureStatus.queued));
      await db.insert(capture('c3', CaptureStatus.accepted));
      expect(await db.unsentCount(), 2);
    });

    test('uploads go oldest first', () async {
      final older = capture('old', CaptureStatus.queued);
      await db.insert(QueuedCapture(
        id: 'old',
        projectId: 'p1',
        kind: 'photo',
        filePath: '/x',
        sha256: 'a' * 64,
        capturedAt: DateTime.utc(2026, 1, 1),
        gpsTime: DateTime.utc(2026, 1, 1),
        lat: 1,
        lon: 1,
        accuracyM: 1,
        deviceId: 'd',
        signature: 's',
      ));
      await db.insert(capture('new', CaptureStatus.queued));
      expect(older.id, 'old');
      expect((await db.due(1 << 62)).map((c) => c.id), ['old', 'new']);
    });
  });

  group('queued claim and verify', () {
    test('an action keeps its id, which is its Idempotency-Key', () async {
      await db.addAction(QueuedAction(
          id: 'key-1', kind: 'claim', path: '/milestones/m1/claim', body: '{}', label: 'Claim Foundation'));
      final a = (await db.actions(openOnly: true)).single;
      expect(a.id, 'key-1');
      expect(a.status, 'queued');
    });

    test('a verification waits while its photos are still on the way', () async {
      await db.insert(capture('c1', CaptureStatus.submitted));
      final r = await sync.resolveChecklist([
        {'item': 'Walls', 'passed': true, 'capture_ids': ['c1']},
      ]);
      expect(r, isNull);
    });

    test('accepted photos are swapped for the server evidence ids', () async {
      await db.insert(capture('c1', CaptureStatus.accepted, evidenceId: 'ev-1'));
      await db.insert(capture('c2', CaptureStatus.accepted, evidenceId: 'ev-2'));
      final r = await sync.resolveChecklist([
        {'item': 'Walls', 'passed': true, 'capture_ids': ['c1', 'c2']},
      ]);
      expect(r, [
        {'item': 'Walls', 'passed': true, 'evidence_ids': ['ev-1', 'ev-2']},
      ]);
      expect(jsonEncode(r), contains('ev-2'));
    });

    test('a rejected photo cancels the verification instead of sending it', () async {
      await db.insert(capture('c1', CaptureStatus.rejected));
      final r = await sync.resolveChecklist([
        {'item': 'Walls', 'passed': true, 'capture_ids': ['c1']},
      ]);
      expect(r, isEmpty);
    });
  });
}
