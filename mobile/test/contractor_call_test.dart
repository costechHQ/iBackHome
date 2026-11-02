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
import 'package:ibackhome_mobile/features/project_screen.dart';
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

Map<String, Object?> project({Map<String, Object?>? contractor}) => {
      'id': 'p1',
      'title': 'Chioma\'s bungalow',
      'address': '14 Chime Avenue',
      'status': 'active',
      'site': null,
      'contractor': contractor,
      'supervisor': null,
    };

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late QueueDb db;
  late ProviderContainer container;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_call');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
  });

  tearDown(() async {
    container.dispose();
    await db.close();
    await tmp.delete(recursive: true);
  });

  Future<Widget> host(WidgetTester tester, {String role = 'supervisor', required Map<String, Object?> proj}) async {
    final w = await tester.runAsync(() async {
      final server = _Server({
        'GET /me': (200, {'id': 'u1', 'role': role, 'status': 'active', 'full_name': 'Ifeoma Eze', 'timezone': 'UTC', 'consent_required': false}),
        'GET /projects/p1': (200, proj),
        'GET /projects/p1/milestones': (200, <Object>[]),
      });
      final tokens = TokenStore(_Store());
      await tokens.save('a', 'r' * 30);
      final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
      container = ProviderContainer(overrides: [
        servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db)),
      ]);
      await container.read(authProvider.notifier).restore();
      return UncontrolledProviderScope(container: container, child: const MaterialApp(home: ProjectScreen(projectId: 'p1')));
    });
    return w!;
  }

  Future<void> settle(WidgetTester tester) async {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await tester.pump();
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await tester.pumpAndSettle();
  }

  testWidgets('a supervisor sees the contractor by name with a Call button', (tester) async {
    await tester.pumpWidget(await host(tester, proj: project(contractor: {'id': 'c1', 'full_name': 'Chukwuemeka Nwosu', 'phone': '+2348030000001'})));
    await settle(tester);
    expect(find.text('Contractor'), findsOneWidget);
    expect(find.text('Chukwuemeka Nwosu'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Call Chukwuemeka Nwosu'), findsOneWidget);
  });

  testWidgets('with no phone there is a name but nothing to call', (tester) async {
    await tester.pumpWidget(await host(tester, proj: project(contractor: {'id': 'c1', 'full_name': 'Chukwuemeka Nwosu', 'phone': null})));
    await settle(tester);
    expect(find.text('Chukwuemeka Nwosu'), findsOneWidget);
    expect(find.textContaining('Call'), findsNothing);
  });

  testWidgets('an unnamed contractor with a phone is "Not named yet" and can still be called', (tester) async {
    await tester.pumpWidget(await host(tester, proj: project(contractor: {'id': 'c1', 'full_name': null, 'phone': '+2348030000001'})));
    await settle(tester);
    expect(find.text('Not named yet'), findsOneWidget);
    expect(find.widgetWithText(OutlinedButton, 'Call the contractor'), findsOneWidget);
  });

  testWidgets('no contractor yet shows no card', (tester) async {
    await tester.pumpWidget(await host(tester, proj: project()));
    await settle(tester);
    expect(find.text('Contractor'), findsNothing);
    expect(find.textContaining('Call'), findsNothing);
  });

  testWidgets('a contractor looking at their own project does not get the card', (tester) async {
    await tester.pumpWidget(await host(tester, role: 'contractor', proj: project(contractor: {'id': 'c1', 'full_name': 'Chukwuemeka Nwosu', 'phone': '+2348030000001'})));
    await settle(tester);
    expect(find.text('Contractor'), findsNothing);
    expect(find.textContaining('Call'), findsNothing);
  });

  Future<Widget> verifyHost(WidgetTester tester, {String? contractorName}) async {
    final w = await tester.runAsync(() async {
      final tokens = TokenStore(_Store());
      await tokens.save('a', 'r' * 30);
      final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = _Server({}));
      container = ProviderContainer(overrides: [
        servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db)),
      ]);
      return UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          home: VerifyScreen(projectId: 'p1', milestoneId: 'm1', milestoneName: 'Plastering', contractorName: contractorName),
        ),
      );
    });
    return w!;
  }

  testWidgets('the verify screen sends back to the contractor by name', (tester) async {
    await tester.pumpWidget(await verifyHost(tester, contractorName: 'Engr. Obi'));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await tester.pump();
    expect(find.text('Send back to Engr. Obi'), findsOneWidget);
    expect(find.text('Send back to contractor'), findsNothing);
  });

  testWidgets('without a name the verify screen says "the contractor"', (tester) async {
    await tester.pumpWidget(await verifyHost(tester));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await tester.pump();
    expect(find.text('Send back to contractor'), findsOneWidget);
  });
}
