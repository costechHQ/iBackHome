import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/capture_rules.dart';
import 'package:ibackhome_mobile/core/geo.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';

void main() {
  final fence = Geo.ringFrom({
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

  CaptureReadiness at(double lat, double lon,
          {double acc = 8, bool mocked = false, List<List<double>>? ring}) =>
      assessReadiness(lat: lat, lon: lon, accuracyM: acc, mocked: mocked, fence: ring ?? fence);

  group('capture readiness', () {
    test('waiting for a fix', () {
      final r = assessReadiness(lat: null, lon: null, accuracyM: null, mocked: false, fence: fence);
      expect(r.state, Readiness.finding);
      expect(r.canShoot, isFalse);
    });

    test('GPS worse than 50 m is refused', () {
      final r = at(6.45045, 7.50045, acc: 51);
      expect(r.state, Readiness.weakGps);
      expect(r.canShoot, isFalse);
    });

    test('exactly 50 m accuracy is allowed', () {
      expect(at(6.45045, 7.50045, acc: 50).canShoot, isTrue);
    });

    test('a mock location is refused, even with a good fix', () {
      final r = at(6.45045, 7.50045, mocked: true);
      expect(r.state, Readiness.mockLocation);
      expect(r.canShoot, isFalse);
    });

    test('inside the site is ready', () {
      expect(at(6.45045, 7.50045).state, Readiness.ready);
    });

    test('within the 25 m allowance is ready', () {
      // About 11 m south of the fence.
      expect(at(6.4500 - 0.0001, 7.50045).state, Readiness.ready);
    });

    test('50 m outside warns but still allows the shot', () {
      final r = at(6.4500 - 0.00045, 7.50045);
      expect(r.state, Readiness.readyOutside);
      expect(r.canShoot, isTrue);
      expect(r.distanceM, inInclusiveRange(45, 55));
    });

    test('a project without a boundary can still be captured (server flags it)', () {
      final r = assessReadiness(lat: 6.45, lon: 7.5, accuracyM: 5, mocked: false, fence: null);
      expect(r.state, Readiness.readyNoSite);
      expect(r.canShoot, isTrue);
    });
  });

  group('three checks', () {
    test('accepted passes all three', () {
      final c = ThreeChecks.from(CaptureStatus.accepted, null);
      expect([c.geofence, c.signed, c.notReused], everyElement(CheckState.pass));
    });

    test('a capture outside the site fails the geofence check', () {
      final c = ThreeChecks.from(CaptureStatus.rejected, 'The capture was taken 52 m outside the site.');
      expect(c.geofence, CheckState.fail);
      expect(c.signed, CheckState.pass);
    });

    test('a bad signature fails the signed check', () {
      final c = ThreeChecks.from(CaptureStatus.rejected, 'The signature is not valid for this device.');
      expect(c.signed, CheckState.fail);
    });

    test('a reused image is flagged, not rejected', () {
      final c = ThreeChecks.from(CaptureStatus.flagged, 'Looks like evidence abc (distance 3); ops must review.');
      expect(c.notReused, CheckState.flagged);
      expect(c.geofence, CheckState.pass);
    });

    test('a project with no site is flagged on the geofence check', () {
      final c = ThreeChecks.from(CaptureStatus.flagged, 'The project has no site geofence yet; ops must review.');
      expect(c.geofence, CheckState.flagged);
    });

    test('waiting captures are all pending', () {
      final c = ThreeChecks.from(CaptureStatus.queued, null);
      expect([c.geofence, c.signed, c.notReused], everyElement(CheckState.pending));
    });
  });
}
