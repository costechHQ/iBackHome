import 'geo.dart';
import 'queue_db.dart';

/// Rules from AND-SUPERVISOR-006: the app refuses weak GPS and mock locations and only warns
/// about the boundary. The server makes the real geofence decision (25 m allowance).
const maxAccuracyM = 50.0;
const fenceAllowanceM = 25.0;

enum Readiness {
  /// No GPS fix yet.
  finding,

  /// Accuracy worse than 50 m: the shutter is refused.
  weakGps,

  /// Android reports the location as simulated: the shutter is refused.
  mockLocation,

  /// Inside the boundary, or within the 25 m allowance.
  ready,

  /// Outside the boundary: the app warns but still allows the shot (the server will reject it).
  readyOutside,

  /// The project has no site boundary yet; the server will flag the capture for ops.
  readyNoSite,
}

class CaptureReadiness {
  const CaptureReadiness(this.state, {this.distanceM = 0, this.accuracyM});

  final Readiness state;
  final double distanceM;
  final double? accuracyM;

  bool get canShoot =>
      state == Readiness.ready || state == Readiness.readyOutside || state == Readiness.readyNoSite;
}

CaptureReadiness assessReadiness({
  required double? lat,
  required double? lon,
  required double? accuracyM,
  required bool mocked,
  required List<List<double>>? fence,
}) {
  if (lat == null || lon == null || accuracyM == null) return const CaptureReadiness(Readiness.finding);
  if (mocked) return CaptureReadiness(Readiness.mockLocation, accuracyM: accuracyM);
  if (accuracyM > maxAccuracyM) return CaptureReadiness(Readiness.weakGps, accuracyM: accuracyM);
  if (fence == null) return CaptureReadiness(Readiness.readyNoSite, accuracyM: accuracyM);
  final d = Geo.distanceToFence(fence, lat, lon);
  return CaptureReadiness(d <= fenceAllowanceM ? Readiness.ready : Readiness.readyOutside,
      distanceM: d, accuracyM: accuracyM);
}

enum CheckState { pass, fail, pending, flagged }

/// The three checks shown wherever evidence appears: inside the site geofence, device-signed,
/// not reused or edited. Derived from the server's status and reason text until the API returns
/// per-check results (design note MX-07).
class ThreeChecks {
  const ThreeChecks(this.geofence, this.signed, this.notReused);

  final CheckState geofence;
  final CheckState signed;
  final CheckState notReused;

  factory ThreeChecks.from(String status, String? reason) {
    final r = (reason ?? '').toLowerCase();
    switch (status) {
      case CaptureStatus.accepted:
        return const ThreeChecks(CheckState.pass, CheckState.pass, CheckState.pass);
      case CaptureStatus.flagged:
        final reused = r.contains('looks like evidence');
        final noSite = r.contains('no site geofence');
        return ThreeChecks(
          noSite ? CheckState.flagged : CheckState.pass,
          CheckState.pass,
          reused ? CheckState.flagged : CheckState.pass,
        );
      case CaptureStatus.rejected:
      case CaptureStatus.failed:
        final outside = r.contains('outside the site');
        final signature = r.contains('signature') ||
            r.contains('hash') ||
            r.contains('device') ||
            r.contains('revoked') ||
            r.contains('capture details');
        return ThreeChecks(
          outside ? CheckState.fail : CheckState.pending,
          signature ? CheckState.fail : (outside ? CheckState.pass : CheckState.pending),
          CheckState.pending,
        );
      default:
        return const ThreeChecks(CheckState.pending, CheckState.pending, CheckState.pending);
    }
  }
}
