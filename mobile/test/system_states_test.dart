import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/api_error.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/home_screen.dart';
import 'package:ibackhome_mobile/features/settings_screen.dart';
import 'package:ibackhome_mobile/features/widgets.dart';
import 'package:ibackhome_mobile/ui/sheets.dart';
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

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  group('confirmation sheet', () {
    Future<bool?> run(WidgetTester tester, {required bool destructive, required String tap}) async {
      bool? result;
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () async => result = await confirmSheet(
                context,
                title: 'Delete this capture?',
                message: 'It hasn\'t uploaded yet.',
                confirmLabel: 'Delete capture',
                cancelLabel: 'Keep it',
                destructive: destructive,
              ),
              child: const Text('open'),
            ),
          ),
        ),
      ));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      await tester.tap(find.text(tap));
      await tester.pumpAndSettle();
      return result;
    }

    testWidgets('the primary button confirms', (tester) async {
      expect(await run(tester, destructive: false, tap: 'Delete capture'), isTrue);
    });

    testWidgets('the safe choice cancels, and dismissing is never a yes', (tester) async {
      expect(await run(tester, destructive: true, tap: 'Keep it'), isFalse);
    });

    testWidgets('a destructive confirmation has a red button and the safe choice under it', (tester) async {
      await tester.pumpWidget(MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => confirmSheet(context, title: 'Revoke?', message: 'm', confirmLabel: 'Revoke device', destructive: true),
              child: const Text('open'),
            ),
          ),
        ),
      ));
      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();
      final red = tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Revoke device'));
      expect(red.style?.backgroundColor?.resolve({}), const Color(0xFFB42318));
      expect(tester.getTopLeft(find.text('Cancel')).dy, greaterThan(tester.getTopLeft(find.text('Revoke device')).dy));
    });
  });

  group('error pages', () {
    testWidgets('no signal says captures are safe and offers the sync queue', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: ErrorRetry(ApiError('network', 'x'), () {}))));
      expect(find.text('Can\'t reach iBackHome'), findsOneWidget);
      expect(find.textContaining('safe on this phone'), findsOneWidget);
      expect(find.text('Open sync queue'), findsOneWidget);
    });

    testWidgets('a server error never offers the sync queue and never blames the person', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: ErrorRetry(ApiError('error', 'stack trace', status: 500, requestId: 'abc123'), () {}))));
      expect(find.text('Something went wrong'), findsOneWidget);
      expect(find.textContaining('Nothing was approved, released or paid'), findsOneWidget);
      expect(find.text('Ref abc123'), findsOneWidget);
      expect(find.text('Open sync queue'), findsNothing);
      expect(find.textContaining('stack trace'), findsNothing);
    });

    test('only the server\'s "not on this project" answer counts as being rotated off', () {
      expect(isRotatedOff(ApiError('not_project_member', 'x', status: 403)), isTrue);
      expect(isRotatedOff(ApiError('forbidden_role', 'x', status: 403)), isFalse);
      expect(isRotatedOff(ApiError('network', 'x')), isFalse);
    });

    testWidgets('rotated off: says why, that unsent captures still upload, and leads back', (tester) async {
      await tester.pumpWidget(const MaterialApp(home: NotOnProjectPage(projectTitle: 'Adaobi\'s terrace')));
      expect(find.text('You\'re no longer on this project'), findsOneWidget);
      expect(find.textContaining('Unsent captures from before still upload'), findsOneWidget);
      expect(find.text('Back to my projects'), findsOneWidget);
    });
  });

  group('settings', () {
    late Directory tmp;
    late QueueDb db;
    late ProviderContainer container;
    late _Server server;

    setUp(() async {
      tmp = await Directory.systemTemp.createTemp('ibh_p4');
      db = await QueueDb.open(path: '${tmp.path}/q.db');
    });

    tearDown(() async {
      container.dispose();
      await db.close();
      await tmp.delete(recursive: true);
    });

    Future<Widget> host(WidgetTester tester, String role) async {
      final w = await tester.runAsync(() async {
        server = _Server({
          'GET /me': (200, {'id': 'u1', 'role': role, 'status': 'active', 'full_name': 'Chidi Nnaji', 'timezone': 'UTC', 'consent_required': false}),
        });
        final tokens = TokenStore(_Store());
        await tokens.save('a', 'r' * 30);
        final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
        container = ProviderContainer(overrides: [
          servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db)),
          // There is no Android Keystore in a test, so the registered key is stood in for.
          deviceProvider.overrideWith((ref) async => 'android-test-4f2a'),
        ]);
        await container.read(authProvider.notifier).restore();
        return UncontrolledProviderScope(container: container, child: const MaterialApp(home: SettingsScreen()));
      });
      return w!;
    }

    testWidgets('a supervisor sees the locked spot-check SMS and a fixed Nigerian time zone', (tester) async {
      await tester.pumpWidget(await host(tester, 'supervisor'));
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
      await tester.pump();
      expect(find.text('SMS for spot checks'), findsOneWidget);
      expect(find.text('Required, can\'t be turned off'), findsOneWidget);
      expect(find.textContaining('Nigerian time (WAT)'), findsOneWidget);
      expect(find.text('Chidi Nnaji'), findsOneWidget);
    });

    testWidgets('a contractor has no spot-check SMS row', (tester) async {
      await tester.pumpWidget(await host(tester, 'contractor'));
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
      await tester.pump();
      expect(find.text('SMS for spot checks'), findsNothing);
      expect(find.text('REGION'), findsOneWidget);
    });
  });
}
