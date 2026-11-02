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
import 'package:ibackhome_mobile/features/home_screen.dart';
import 'package:ibackhome_mobile/features/settings_screen.dart';
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
  final List<RequestOptions> seen = [];

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body, Future<void>? cancel) async {
    seen.add(options);
    final hit = routes['${options.method} ${options.path}'] ?? (404, {'error': {'code': 'not_found', 'message': 'No.'}});
    return ResponseBody.fromString(jsonEncode(hit.$2), hit.$1, headers: {
      Headers.contentTypeHeader: ['application/json'],
    });
  }

  @override
  void close({bool force = false}) {}
}

Map<String, Object?> phone(String id, {String? revokedAt}) => {
      'id': id,
      'device_id': 'install-$id',
      'registered_at': '2026-09-01T10:00:00Z',
      'revoked_at': revokedAt,
    };

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late QueueDb db;
  late ProviderContainer container;
  late _Server server;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_phones');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
  });

  tearDown(() async {
    container.dispose();
    await db.close();
    await tmp.delete(recursive: true);
  });

  Future<Widget> host(WidgetTester tester, Map<String, (int, Object)> extra) async {
    final w = await tester.runAsync(() async {
      server = _Server({
        'GET /me': (200, {'id': 'u1', 'role': 'supervisor', 'status': 'active', 'full_name': 'Ifeoma Eze', 'timezone': 'UTC', 'consent_required': false}),
        'GET /me/notification-preferences': (200, {'push_enabled': true, 'hide_previews': false}),
        'PUT /me/notification-preferences': (200, {'push_enabled': false, 'hide_previews': false}),
        ...extra,
      });
      final tokens = TokenStore(_Store());
      await tokens.save('a', 'r' * 30);
      final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
      container = ProviderContainer(overrides: [
        servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db)),
        deviceProvider.overrideWith((ref) async => 'android-test-4f2a'),
      ]);
      await container.read(authProvider.notifier).restore();
      return UncontrolledProviderScope(container: container, child: const MaterialApp(home: SettingsScreen()));
    });
    return w!;
  }

  Future<void> settle(WidgetTester tester) async {
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await tester.pump();
  }

  testWidgets('lists other phones: an active one with Revoke, a revoked one marked', (tester) async {
    await tester.pumpWidget(await host(tester, {
      'GET /devices': (200, [phone('d1'), phone('d2', revokedAt: '2026-09-20T08:00:00Z')]),
    }));
    await settle(tester);
    await tester.scrollUntilVisible(find.text('Revoked'), 200, scrollable: find.byType(Scrollable).first);
    expect(find.text('Another phone'), findsNWidgets(2));
    expect(find.text('Revoked'), findsOneWidget);
    // This phone has its own Revoke row; the list adds one more for the active old phone.
    expect(find.text('Revoke'), findsNWidgets(2));
  });

  testWidgets('no other phones says so', (tester) async {
    await tester.pumpWidget(await host(tester, {'GET /devices': (200, <Object>[])}));
    await settle(tester);
    await tester.scrollUntilVisible(find.text('No other phones are set up on your account.'), 200, scrollable: find.byType(Scrollable).first);
    expect(find.text('No other phones are set up on your account.'), findsOneWidget);
  });

  testWidgets('revoking asks first, then posts the revoke with an Idempotency-Key', (tester) async {
    await tester.pumpWidget(await host(tester, {
      'GET /devices': (200, [phone('d1')]),
      'POST /devices/d1/revoke': (200, phone('d1', revokedAt: '2026-11-02T09:00:00Z')),
    }));
    await settle(tester);
    await tester.scrollUntilVisible(find.text('Another phone'), 200, scrollable: find.byType(Scrollable).first);
    // The Revoke on the old phone's row is the second one (this phone's row comes first).
    await tester.tap(find.widgetWithText(OutlinedButton, 'Revoke').last);
    await tester.pumpAndSettle();
    expect(find.text('Revoke this other phone?'), findsOneWidget);
    expect(server.seen.where((r) => r.method == 'POST'), isEmpty, reason: 'nothing is sent before the person confirms');

    // After the revoke the list is read again and shows the phone as revoked.
    server.routes['GET /devices'] = (200, [phone('d1', revokedAt: '2026-11-02T09:00:00Z')]);
    await tester.tap(find.text('Revoke phone'));
    await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
    await tester.pumpAndSettle();

    final post = server.seen.singleWhere((r) => r.method == 'POST');
    expect(post.path, '/devices/d1/revoke');
    expect(post.headers['Idempotency-Key'], 'revoke-d1');
    expect(find.text('Revoked'), findsOneWidget);
  });

  testWidgets('a failed load explains and offers Retry', (tester) async {
    await tester.pumpWidget(await host(tester, {
      'GET /devices': (500, {'error': {'code': 'server_error', 'message': 'boom'}}),
    }));
    await settle(tester);
    await tester.scrollUntilVisible(find.text('Retry'), 200, scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('couldn\'t be loaded'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('the push switch saves both settings', (tester) async {
    await tester.pumpWidget(await host(tester, {'GET /devices': (200, <Object>[])}));
    await settle(tester);
    for (var i = 0; i < 3; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await settle(tester);
    }
    expect(find.text('Push notifications'), findsOneWidget);
    expect(find.text('Hide previews on lock screen'), findsOneWidget);
    await tester.tap(find.byType(Switch).first);
    for (var i = 0; i < 3; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await settle(tester);
    }
    final put = server.seen.singleWhere((r) => r.method == 'PUT');
    expect(put.path, '/me/notification-preferences');
    expect(put.data, {'push_enabled': false, 'hide_previews': false});
  });
}
