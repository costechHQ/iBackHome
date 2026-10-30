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

  /// The designed wording for this error (Docs/design/04-api-mapping/error-codes-to-ui.md).
  /// Falls back to the server's own message, which is written to be shown.
  String get friendlyMessage {
    switch (code) {
      case 'network':
        return 'You\'re offline. What you captured is safe on this phone and will upload when you have signal.';
      case 'unauthorized':
        return 'Please sign in again. Anything you captured is safe on this phone.';
      case 'not_project_member':
        return 'You\'re not on this project any more. If you were rotated off, nothing you captured is lost.';
      case 'forbidden_role':
        return 'This isn\'t available for your account.';
      case 'notifications_not_configured':
        return 'That way of sending the code isn\'t available. Try a different channel.';
      case 'notification_failed':
        return 'We couldn\'t send your code. Try again, or choose a different channel.';
      case 'too_many_attempts':
        return 'Too many wrong codes. Ask for a new code.';
      case 'project_not_active':
        return 'This project is paused, so milestone actions are on hold.';
      case 'device_revoked':
        return message;
    }
    if (status == 429) return 'Too many tries. Wait a little and try again.';
    if (status != null && status! >= 500) {
      return 'Something went wrong on our side. Nothing was approved, released or paid.';
    }
    if (status == 404) return 'We can\'t find that. It may have been removed.';
    return message;
  }

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
