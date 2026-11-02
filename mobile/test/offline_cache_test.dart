import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/api_error.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
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

/// Answers from a table, or drops the connection when [offline] is set.
class _Server implements HttpClientAdapter {
  bool offline = false;
  final Map<String, (int, Object)> routes = {};

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body, Future<void>? cancel) async {
    if (offline) {
      throw DioException.connectionError(requestOptions: options, reason: 'no signal');
    }
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
  late _Server server;
  late Services services;

  setUp(() async {
    tmp = await Directory.systemTemp.createTemp('ibh_cache');
    db = await QueueDb.open(path: '${tmp.path}/q.db');
    server = _Server();
    final tokens = TokenStore(_Store());
    final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
    services = Services.forTesting(tokens: tokens, api: api, db: db, saveReads: true);
  });

  tearDown(() async {
    await db.close();
    await tmp.delete(recursive: true);
  });

  Future<void> settle() => Future<void>.delayed(const Duration(milliseconds: 50)); // the save is not awaited

  test('an answer from the server is saved, and the screens are not marked stale', () async {
    server.routes['GET /projects'] = (200, {'items': [{'id': 'p1', 'title': 'Enugu house'}]});
    final page = await services.cachedGet<Map<String, dynamic>>('/projects', query: {'limit': 50});
    await settle();
    expect((page['items'] as List).length, 1);
    expect(services.staleSince.value, isNull);
    expect(await db.getCache('/projects?limit=50'), isNotNull);
  });

  test('with no signal the last saved answer comes back and is marked stale', () async {
    server.routes['GET /projects'] = (200, {'items': [{'id': 'p1', 'title': 'Enugu house'}]});
    await services.cachedGet<Map<String, dynamic>>('/projects', query: {'limit': 50});
    await settle();

    server.offline = true;
    final page = await services.cachedGet<Map<String, dynamic>>('/projects', query: {'limit': 50});
    expect(((page['items'] as List).first as Map)['title'], 'Enugu house');
    expect(services.staleSince.value, isNotNull);

    server.offline = false;
    await services.cachedGet<Map<String, dynamic>>('/projects', query: {'limit': 50});
    expect(services.staleSince.value, isNull);
  });

  test('with no signal and nothing saved, the offline error is shown', () async {
    server.offline = true;
    expect(
      () => services.cachedGet<List<dynamic>>('/projects/p9/milestones'),
      throwsA(isA<ApiError>().having((e) => e.isNetwork, 'isNetwork', true)),
    );
  });

  test('a server refusal is never hidden by the saved copy', () async {
    server.routes['GET /projects/p1'] = (200, {'id': 'p1'});
    await services.cachedGet<Map<String, dynamic>>('/projects/p1');
    await settle();

    server.routes['GET /projects/p1'] = (403, {'error': {'code': 'not_project_member', 'message': 'No.'}});
    await expectLater(
      services.cachedGet<Map<String, dynamic>>('/projects/p1'),
      throwsA(isA<ApiError>().having((e) => e.code, 'code', 'not_project_member')),
    );
    expect(services.staleSince.value, isNull);
  });

  test('clearing the cache forgets every saved answer', () async {
    await db.putCache('/me', '{"role":"supervisor"}');
    await db.clearCache();
    expect(await db.getCache('/me'), isNull);
  });
}
