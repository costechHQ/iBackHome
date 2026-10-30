import 'package:dio/dio.dart';

/// The API's one error shape: `{"error": {"code", "message"}}`. Branch on [code], show [message].
class ApiError implements Exception {
  ApiError(this.code, this.message, {this.status, this.requestId});

  final String code;
  final String message;
  final int? status;
  final String? requestId;

  bool get isNetwork => code == 'network';

  /// True when the problem is the connection or the server being busy, so a retry may work.
  bool get isRetryable => isNetwork || (status != null && status! >= 500) || status == 429;

  factory ApiError.from(Object error) {
    if (error is ApiError) return error;
    if (error is DioException) {
      final res = error.response;
      final body = res?.data;
      if (body is Map && body['error'] is Map) {
        final e = body['error'] as Map;
        return ApiError(
          '${e['code'] ?? 'error'}',
          '${e['message'] ?? 'Something went wrong.'}',
          status: res?.statusCode,
          requestId: res?.headers.value('x-request-id'),
        );
      }
      if (res != null) {
        return ApiError('http_${res.statusCode}', 'The server answered ${res.statusCode}.',
            status: res.statusCode, requestId: res.headers.value('x-request-id'));
      }
      return ApiError('network', 'No connection to the server. Check your signal and try again.');
    }
    return ApiError('error', '$error');
  }

  @override
  String toString() => '$code: $message';
}
