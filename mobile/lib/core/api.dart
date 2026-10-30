import 'dart:async';

import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import 'api_error.dart';
import 'config.dart';
import 'token_store.dart';

const _uuid = Uuid();

/// HTTP client for the iBackHome API.
///
/// Rules from Docs/api-guide.md: bearer token and `X-Device-Id` on every call; one refresh in
/// flight at a time (a reused refresh token signs the user out everywhere), never retried blindly;
/// a new `Idempotency-Key` per user action, the same key when that action is retried.
class Api {
  Api(this.tokens, {Dio? dio, this.onSignedOut}) : dio = dio ?? Dio(_options()) {
    this.dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = tokens.accessToken;
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        options.headers['X-Device-Id'] = await tokens.deviceId();
        handler.next(options);
      },
      onError: (e, handler) async {
        final path = e.requestOptions.path;
        final retried = e.requestOptions.extra['retried'] == true;
        if (e.response?.statusCode == 401 && !retried && !path.startsWith('/auth/')) {
          if (await _refresh()) {
            final opts = e.requestOptions..extra['retried'] = true;
            opts.headers['Authorization'] = 'Bearer ${tokens.accessToken}';
            try {
              return handler.resolve(await this.dio.fetch<dynamic>(opts));
            } on DioException catch (again) {
              return handler.next(again);
            }
          }
        }
        handler.next(e);
      },
    ));
  }

  static BaseOptions _options() => BaseOptions(
        baseUrl: Config.apiBaseUrl,
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 30),
        headers: {'Accept': 'application/json'},
      );

  final TokenStore tokens;
  final Dio dio;
  final void Function()? onSignedOut;
  Future<bool>? _refreshing;

  /// Single flight: callers that hit a 401 together share one refresh call.
  Future<bool> _refresh() => _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);

  Future<bool> _doRefresh() async {
    final refresh = await tokens.refreshToken();
    if (refresh == null) return false;
    try {
      final res = await Dio(_options()).post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refresh},
      );
      await tokens.save(res.data!['access_token'] as String, res.data!['refresh_token'] as String);
      return true;
    } on DioException catch (e) {
      // No answer at all may be temporary: keep the session. Only a refusal ends it.
      if (e.response == null) return false;
      await tokens.clear();
      onSignedOut?.call();
      return false;
    }
  }

  static String newKey() => _uuid.v4();

  Future<T> get<T>(String path, {Map<String, dynamic>? query}) => _run(() async {
        final res = await dio.get<T>(path, queryParameters: query);
        return res.data as T;
      });

  Future<T> post<T>(String path, {Object? body, String? idempotencyKey}) => _run(() async {
        final res = await dio.post<T>(
          path,
          data: body,
          options: Options(headers: {'Idempotency-Key': idempotencyKey ?? newKey()}),
        );
        return res.data as T;
      });

  Future<T> _run<T>(Future<T> Function() call) async {
    try {
      return await call();
    } catch (e) {
      throw ApiError.from(e);
    }
  }
}
