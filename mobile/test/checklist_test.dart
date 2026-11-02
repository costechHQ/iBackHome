import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/capture_target.dart';
import 'package:ibackhome_mobile/features/milestone_screen.dart';
import 'package:ibackhome_mobile/features/verify_screen.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class _Store implements SecretStore {
  final Map<String, String> data = {};
  @override
  Future<String?> read(String key) async => data[key];
  @override
  Future<void> write(String key, String value) async => data[key] = value;
  @override
  Future<void> delete(String key) async => data.remove(key);
}

class _Server implements HttpClientAdapter {
  _Server(this.routes);
  final Map<String, (int, Object)> routes;

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body, Future<void>? cancel) async {
    final hit = routes['${options.method} ${options.path}'] ?? (404, {'error': {'code': 'not_found', 'message': 'No.'}});
    return ResponseBody.fromString(jsonEncode(hit.$2), hit.$1, headers: {
      Headers.contentTypeHeader: ['application/json'],
    });
  }

  @override
  void close({bool force = false}) {}
}

const foundation = ['Trench depth as drawn', 'Reinforcement tied and spaced', 'Concrete poured and cured'];

Map<String, Object?> milestone({List<String>? checklist, bool omit = false}) => {
      'id': 'm1',
      'project_id': 'p1',
      'sequence': 1,
      'name': 'Foundation',
      'amount_minor': 800000000,
      'currency': 'NGN',
      'status': 'claimed',
      'claimed_at': '2026-11-01T09:00:00Z',
      'latest_verification': null,
      if (!omit) 'checklist': checklist,
    };

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  group('milestoneChecklist', () {
    test('uses the list the server sent', () {
      expect(milestoneChecklist({'checklist': foundation}), foundation);
    });

    test('falls back to the generic list when the server sent none', () {
      expect(milestoneChecklist({}), defaultChecklist);
      expect(milestoneChecklist({'checklist': null}), defaultChecklist);
      expect(milestoneChecklist({'checklist': <String>[]}), defaultChecklist);
    });

    test('drops blank items, and falls back if nothing is left', () {
      expect(milestoneChecklist({'checklist': ['Slab level', '  ', '']}), ['Slab level']);
      expect(milestoneChecklist({'checklist': ['', '   ']}), defaultChecklist);
    });

    test('the fallback is the same four items the server falls back to', () {
      expect(defaultChecklist, [
        'Work matches the bill of quantities',
        'Materials are as specified',
        'Workmanship is acceptable',
        'Site is safe and tidy',
      ]);
    });
  });

  group('screens', () {
    late Directory tmp;
    late QueueDb db;
    late ProviderContainer container;

    setUp(() async {
      tmp = await Directory.systemTemp.createTemp('ibh_checklist');
      db = await QueueDb.open(path: '${tmp.path}/q.db');
    });

    tearDown(() async {
      container.dispose();
      await db.close();
      await tmp.delete(recursive: true);
    });

    Future<Widget> host(WidgetTester tester, Widget child, {String role = 'supervisor', Map<String, Object?>? ms}) async {
      final w = await tester.runAsync(() async {
        final server = _Server({
          'GET /me': (200, {'id': 'u1', 'role': role, 'status': 'active', 'full_name': 'Ifeoma Eze', 'timezone': 'UTC', 'consent_required': false}),
          'GET /projects/p1': (200, {'id': 'p1', 'title': 'Bungalow', 'address': '1 Road', 'status': 'active', 'site': null, 'contractor': null, 'supervisor': null}),
          'GET /projects/p1/milestones': (200, [ms ?? milestone(checklist: foundation.toList())]),
        });
        final tokens = TokenStore(_Store());
        await tokens.save('a', 'r' * 30);
        final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
        container = ProviderContainer(overrides: [servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db))]);
        await container.read(authProvider.notifier).restore();
        return UncontrolledProviderScope(container: container, child: MaterialApp(home: child));
      });
      return w!;
    }

    Future<void> settle(WidgetTester tester) async {
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
      await tester.pump();
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
      await tester.pumpAndSettle();
    }

    testWidgets('a supervisor sees the milestone\'s own checklist and how much of it is captured', (tester) async {
      await tester.pumpWidget(await host(tester, const MilestoneScreen(projectId: 'p1', milestoneId: 'm1')));
      await settle(tester);
      for (final item in foundation) {
        expect(find.text(item), findsOneWidget);
      }
      expect(find.text('0 of 3 captured'), findsOneWidget);
      expect(find.text('Workmanship is acceptable'), findsNothing); // not the generic list
    });

    testWidgets('a milestone with no checklist from the server shows the generic four', (tester) async {
      await tester.pumpWidget(await host(tester, const MilestoneScreen(projectId: 'p1', milestoneId: 'm1'), ms: milestone(omit: true)));
      await settle(tester);
      expect(find.text('0 of 4 captured'), findsOneWidget);
      expect(find.text('Workmanship is acceptable'), findsOneWidget);
    });

    testWidgets('a contractor is shown the same list, as what the supervisor will capture', (tester) async {
      await tester.pumpWidget(await host(tester, const MilestoneScreen(projectId: 'p1', milestoneId: 'm1'), role: 'contractor', ms: {...milestone(checklist: foundation.toList()), 'status': 'funded'}));
      await settle(tester);
      expect(find.text('WHAT THE SUPERVISOR WILL CAPTURE'), findsOneWidget);
      for (final item in foundation) {
        expect(find.text(item), findsOneWidget);
      }
    });

    testWidgets('the verify screen checks the milestone\'s own items, not the generic ones', (tester) async {
      await tester.pumpWidget(await host(tester, const VerifyScreen(projectId: 'p1', milestoneId: 'm1', milestoneName: 'Foundation', checklist: foundation)));
      await settle(tester);
      for (final item in foundation) {
        expect(find.textContaining(item), findsWidgets);
      }
      expect(find.textContaining('Workmanship is acceptable'), findsNothing);
    });

    testWidgets('the verify screen falls back to the generic items when it is given none', (tester) async {
      await tester.pumpWidget(await host(tester, const VerifyScreen(projectId: 'p1', milestoneId: 'm1', milestoneName: 'Foundation')));
      await settle(tester);
      expect(find.textContaining('Workmanship is acceptable'), findsWidgets);
    });
  });
}
