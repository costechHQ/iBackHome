import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/places.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/profile_screen.dart';
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
  final List<RequestOptions> seen = [];
  Map<String, dynamic> me = {
    'id': 'u1',
    'phone': '+2348030000001',
    'email': null,
    'full_name': 'Ada Obi',
    'role': 'contractor',
    'status': 'active',
    'timezone': 'Africa/Lagos',
    'country': 'NG',
  };

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? body,
    Future<void>? cancel,
  ) async {
    seen.add(options);
    if (options.method == 'PATCH' && options.path == '/me') {
      me = {...me, ...(options.data as Map<String, dynamic>)};
    }
    final found = options.path == '/me';
    return ResponseBody.fromString(
      jsonEncode(
        found
            ? me
            : {
                'error': {'code': 'not_found', 'message': 'No.'},
              },
      ),
      found ? 200 : 404,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late QueueDb db;
  late _Server server;
  late ProviderContainer container;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_profile');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
    server = _Server();
    final tokens = TokenStore(_Store());
    await tokens.save('a', 'r' * 30);
    final api = Api(
      tokens,
      dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server,
    );
    container = ProviderContainer(
      overrides: [
        servicesProvider.overrideWithValue(
          Services.forTesting(tokens: tokens, api: api, db: db),
        ),
      ],
    );
    await container.read(authProvider.notifier).restore();
  });

  tearDown(() async {
    container.dispose();
    await db.close();
    await tmp.delete(recursive: true);
  });

  Widget screen() => UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: ProfileScreen()),
  );

  testWidgets('shows what the server holds, with sign-in details read-only', (
    tester,
  ) async {
    await tester.pumpWidget(screen());
    expect(find.text('Ada Obi'), findsOneWidget);
    expect(find.text('+2348030000001'), findsOneWidget);
    expect(find.textContaining('cannot be changed here'), findsOneWidget);
  });

  testWidgets(
    'saving sends only name, country and time zone with an Idempotency-Key',
    (tester) async {
      await tester.pumpWidget(screen());
      await tester.enterText(find.byType(TextFormField), 'Ada Okafor');
      await tester.ensureVisible(find.text('Save'));
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();
      final patch = server.seen.singleWhere((r) => r.method == 'PATCH');
      expect(patch.data, {
        'full_name': 'Ada Okafor',
        'country': 'NG',
        'timezone': 'Africa/Lagos',
      });
      expect(patch.headers['Idempotency-Key'], isNotEmpty);
      expect(container.read(authProvider).me?['full_name'], 'Ada Okafor');
      expect(find.textContaining('Saved'), findsOneWidget);
    },
  );

  testWidgets('an empty name is refused without calling the server', (
    tester,
  ) async {
    await tester.pumpWidget(screen());
    await tester.enterText(find.byType(TextFormField), '   ');
    await tester.ensureVisible(find.text('Save'));
    await tester.tap(find.text('Save'));
    await tester.pump();
    expect(find.text('Enter your full name.'), findsOneWidget);
    expect(server.seen.where((r) => r.method == 'PATCH'), isEmpty);
  });

  test('a saved value outside the list is kept as an option', () {
    expect(withCurrent(profileCountries, 'PT').containsKey('PT'), isTrue);
    expect(
      withCurrent(profileTimeZones, 'Africa/Lagos').length,
      profileTimeZones.length,
    );
  });
}
