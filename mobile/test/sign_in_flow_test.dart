import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/app.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/api_error.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class MemoryStore implements SecretStore {
  final Map<String, String> data = {};
  @override
  Future<String?> read(String key) async => data[key];
  @override
  Future<void> write(String key, String value) async => data[key] = value;
  @override
  Future<void> delete(String key) async => data.remove(key);
}

/// Answers API calls from a table of `METHOD path` -> (status, json), and records the requests.
class FakeServer implements HttpClientAdapter {
  FakeServer(this.routes);
  final Map<String, (int, Object)> routes;
  final List<RequestOptions> seen = [];

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body, Future<void>? cancel) async {
    seen.add(options);
    final hit = routes['${options.method} ${options.path}'] ?? (404, {'error': {'code': 'not_found', 'message': 'No such route.'}});
    return ResponseBody.fromString(jsonEncode(hit.$2), hit.$1, headers: {
      Headers.contentTypeHeader: ['application/json'],
    });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late QueueDb db;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_widget');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
  });

  tearDown(() async {
    await db.close();
    await tmp.delete(recursive: true);
  });

  Future<(FakeServer, Widget)> app(Map<String, (int, Object)> routes) async {
    final server = FakeServer(routes);
    final tokens = TokenStore(MemoryStore());
    final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test/api/v1'))..httpClientAdapter = server);
    final services = Services.forTesting(tokens: tokens, api: api, db: db);
    return (server, ProviderScope(overrides: [servicesProvider.overrideWithValue(services)], child: const IbhApp()));
  }

  testWidgets('signed-out users land on sign-in with the logo and a disabled Send code', (tester) async {
    final (_, widget) = await app({});
    await tester.pumpWidget(widget);
    await tester.pumpAndSettle();
    expect(find.text('Send code'), findsOneWidget);
    expect(tester.widget<FilledButton>(find.byType(FilledButton)).onPressed, isNull);
    expect(find.bySemanticsLabel('iBackHome'), findsOneWidget);
  });

  testWidgets('asks for a code on the chosen channel, then shows the code field', (tester) async {
    final (server, widget) = await app({
      'POST /auth/otp/request': (202, {'status': 'sent', 'expires_in': 300}),
    });
    await tester.pumpWidget(widget);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, '08030000002');
    await tester.tap(find.text('WhatsApp'));
    await tester.pump();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();

    final sent = server.seen.single;
    expect(sent.path, '/auth/otp/request');
    expect(sent.data, {'identifier': '08030000002', 'channel': 'whatsapp'});
    expect(sent.headers['Idempotency-Key'], isNotEmpty);
    expect(find.text('6-digit code'), findsOneWidget);
  });

  testWidgets('a channel the server cannot use shows the designed message', (tester) async {
    final (_, widget) = await app({
      'POST /auth/otp/request': (503, {'error': {'code': 'notifications_not_configured', 'message': 'raw'}}),
    });
    await tester.pumpWidget(widget);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, '08030000002');
    await tester.pump();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    expect(find.textContaining('isn\'t available. Try a different channel'), findsOneWidget);
  });

  testWidgets('a client account is told this app is for supervisors and contractors', (tester) async {
    final (_, widget) = await app({
      'POST /auth/otp/request': (202, {'status': 'sent', 'expires_in': 300}),
      'POST /auth/otp/verify': (200, {'access_token': 'a', 'refresh_token': 'r' * 30, 'token_type': 'bearer', 'expires_in': 900}),
      'GET /me': (200, {'id': 'u1', 'role': 'client', 'status': 'active', 'timezone': 'UTC', 'consent_required': false}),
    });
    await tester.pumpWidget(widget);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, 'client@example.com');
    await tester.pump();
    await tester.tap(find.text('Send code'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).last, '123456');
    await tester.pump();
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('This app is for supervisors and contractors.'), findsOneWidget);
  });

  group('error wording', () {
    test('uses the designed copy and never the raw server text for 5xx', () {
      final e = ApiError('error', 'stack trace here', status: 500);
      expect(e.friendlyMessage, contains('Nothing was approved, released or paid'));
    });

    test('offline explains that captures are safe', () {
      expect(ApiError('network', 'x').friendlyMessage, contains('safe on this phone'));
    });

    test('rotated off a project', () {
      expect(ApiError('not_project_member', 'x', status: 403).friendlyMessage, contains('not on this project'));
    });

    test('unknown codes keep the server message, which is written to be shown', () {
      expect(ApiError('milestone_not_verified', 'Roofing was already approved.', status: 409).friendlyMessage,
          'Roofing was already approved.');
    });
  });
}
