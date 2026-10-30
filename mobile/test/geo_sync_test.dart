import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api_error.dart';
import 'package:ibackhome_mobile/core/geo.dart';
import 'package:ibackhome_mobile/core/sync_service.dart';

void main() {
  // A roughly 100 m square near Enugu.
  final square = Geo.ringFrom({
    'type': 'Polygon',
    'coordinates': [
      [
        [7.5000, 6.4500],
        [7.5009, 6.4500],
        [7.5009, 6.4509],
        [7.5000, 6.4509],
        [7.5000, 6.4500],
      ]
    ],
  });

  group('geofence warning', () {
    test('inside is zero metres away', () {
      expect(Geo.inside(square, 6.45045, 7.50045), isTrue);
      expect(Geo.distanceToFence(square, 6.45045, 7.50045), 0);
    });

    test('about 50 m outside reads as about 50 m', () {
      // 0.00045 degrees of latitude is about 50 m.
      final d = Geo.distanceToFence(square, 6.4500 - 0.00045, 7.50045);
      expect(d, inInclusiveRange(45, 55));
      expect(Geo.inside(square, 6.4500 - 0.00045, 7.50045), isFalse);
    });
  });

  group('retry backoff', () {
    test('starts at 5 s, doubles and stops at 10 minutes', () {
      expect(SyncService.backoffMs(0), 5000);
      expect(SyncService.backoffMs(1), 10000);
      expect(SyncService.backoffMs(3), 40000);
      expect(SyncService.backoffMs(20), 600000);
    });
  });

  group('ApiError', () {
    test('reads the API error shape', () {
      final e = ApiError.from(DioException(
        requestOptions: RequestOptions(path: '/x'),
        response: Response(
          requestOptions: RequestOptions(path: '/x'),
          statusCode: 409,
          data: {'error': {'code': 'invalid_transition', 'message': 'Not now.'}},
        ),
      ));
      expect(e.code, 'invalid_transition');
      expect(e.message, 'Not now.');
      expect(e.isRetryable, isFalse);
    });

    test('no response means a network problem that can be retried', () {
      final e = ApiError.from(DioException(requestOptions: RequestOptions(path: '/x')));
      expect(e.isNetwork, isTrue);
      expect(e.isRetryable, isTrue);
    });
  });
}
