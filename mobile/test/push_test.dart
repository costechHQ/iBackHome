import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/push.dart';
import 'package:ibackhome_mobile/core/push_route.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/milestone_screen.dart';
import 'package:ibackhome_mobile/features/project_screen.dart';
import 'package:ibackhome_mobile/features/reports_screen.dart';
import 'package:ibackhome_mobile/features/spot_checks_screen.dart';
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
  final List<String> seen = [];
  final List<Object?> bodies = [];
  bool offline = false;

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body, Future<void>? cancel) async {
    if (offline) throw DioException.connectionError(requestOptions: options, reason: 'offline');
    seen.add('${options.method} ${options.path}');
    bodies.add(options.data);
    final out = switch ('${options.method} ${options.path}') {
      'POST /devices' => {'id': 'pk1', 'device_id': 'x', 'registered_at': '2026-09-01T10:00:00Z', 'revoked_at': null},
      'POST /me/push-tokens' => {'device_pk': 'pk1'},
      _ => <String, Object>{},
    };
    final status = options.method == 'DELETE' ? 204 : 200;
    return ResponseBody.fromString(status == 204 ? '' : jsonEncode(out), status, headers: {
      Headers.contentTypeHeader: ['application/json'],
    });
  }

  @override
  void close({bool force = false}) {}
}

class _FakePush implements PushBackend {
  _FakePush({this.allowed = true});
  final bool allowed;
  String? current = 'tok-1';
  PushMessage? launch;
  bool deleted = false;
  final refresh = StreamController<String>.broadcast();
  final fg = StreamController<PushMessage>.broadcast();
  final tap = StreamController<PushMessage>.broadcast();

  @override
  Future<bool> start() async => allowed;
  @override
  Future<String?> token() async => current;
  @override
  Stream<String> get tokenRefreshed => refresh.stream;
  @override
  Stream<PushMessage> get foreground => fg.stream;
  @override
  Stream<PushMessage> get opened => tap.stream;
  @override
  Future<PushMessage?> launchedBy() async => launch;
  @override
  Future<void> deleteToken() async => deleted = true;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(
      const MethodChannel('ng.ibackhome/keystore'), (call) async => call.method == 'ensureKey' ? 'cHVibGljLWtleQ==' : null);
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tmp;
  late QueueDb db;
  late _Server server;
  late Services services;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_push');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
    server = _Server();
    final tokens = TokenStore(_Store());
    await tokens.save('a', 'r' * 30);
    final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
    services = Services.forTesting(tokens: tokens, api: api, db: db);
  });

  tearDown(() async {
    await db.close();
    await tmp.delete(recursive: true);
  });

  Future<void> settle() => Future<void>.delayed(const Duration(milliseconds: 50));

  test('registers the token against this phone\'s device id (registering the phone first if needed)', () async {
    final push = PushService(services, _FakePush());
    await push.start();
    expect(server.seen, ['POST /devices', 'POST /me/push-tokens']);
    expect(server.bodies.last, {'device_pk': 'pk1', 'token': 'tok-1'});
    expect(push.registeredToken, 'tok-1');
  });

  test('a refreshed token replaces the old one; the same token is not sent twice', () async {
    final fake = _FakePush();
    final push = PushService(services, fake);
    await push.start();
    fake.refresh.add('tok-1');
    fake.refresh.add('tok-2');
    await settle();
    expect(server.seen.where((s) => s == 'POST /me/push-tokens').length, 2);
    expect(push.registeredToken, 'tok-2');
  });

  test('refused permission or no Firebase project: nothing is sent and nothing throws', () async {
    final push = PushService(services, _FakePush(allowed: false));
    await push.start();
    expect(server.seen, isEmpty);
    expect(push.registeredToken, isNull);
  });

  test('offline at start: push stays quiet, a later refresh registers', () async {
    final fake = _FakePush();
    server.offline = true;
    final push = PushService(services, fake);
    await push.start();
    expect(push.registeredToken, isNull);
    server.offline = false;
    fake.refresh.add('tok-9');
    await settle();
    expect(push.registeredToken, 'tok-9');
  });

  test('sign-out forgets the token on the server and on the phone', () async {
    final fake = _FakePush();
    final push = PushService(services, fake);
    await push.start();
    await push.stop();
    expect(server.seen.last, 'DELETE /me/push-tokens/pk1');
    expect(fake.deleted, isTrue);
    expect(push.registeredToken, isNull);
  });

  test('a tapped push, a push that launched the app and a foreground push reach the app', () async {
    final fake = _FakePush()..launch = const PushMessage({'project_id': 'p1'});
    final push = PushService(services, fake);
    final opened = <PushMessage>[];
    final arrived = <PushMessage>[];
    push.opened.listen(opened.add);
    push.arrived.listen(arrived.add);
    await push.start();
    fake.tap.add(const PushMessage({'milestone_id': 'm1', 'project_id': 'p1'}));
    fake.fg.add(const PushMessage({}, body: 'New update'));
    await settle();
    expect(opened.length, 2);
    expect(arrived.single.body, 'New update');
  });

  test('every push opens the exact screen it is about', () {
    expect(screenForPush(const PushMessage({'project_id': 'p', 'milestone_id': 'm'})), isA<MilestoneScreen>());
    expect(screenForPush(const PushMessage({'project_id': 'p', 'report_id': 'r'})), isA<ReportsScreen>());
    expect(screenForPush(const PushMessage({'spot_check_id': 's'})), isA<SpotChecksScreen>());
    expect(screenForPush(const PushMessage({'project_id': 'p'})), isA<ProjectScreen>());
    expect(screenForPush(const PushMessage({})), isNull);
  });
}
