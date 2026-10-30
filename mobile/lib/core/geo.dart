import 'dart:math' as math;

/// The device only warns; the server decides (CLAUDE.md, Evidence integrity). These helpers
/// tell the supervisor early that they are probably outside the fence.
class Geo {
  Geo._();

  /// [ring] is a GeoJSON linear ring: a list of `[lon, lat]`.
  static List<List<double>> ringFrom(Map<String, dynamic> polygon) {
    final coords = polygon['coordinates'] as List;
    return [
      for (final p in (coords.first as List)) [(p[0] as num).toDouble(), (p[1] as num).toDouble()]
    ];
  }

  static bool inside(List<List<double>> ring, double lat, double lon) {
    var in_ = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      final xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if ((yi > lat) != (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) in_ = !in_;
    }
    return in_;
  }

  /// Metres from the point to the nearest fence edge (0 inside).
  static double distanceToFence(List<List<double>> ring, double lat, double lon) {
    if (inside(ring, lat, lon)) return 0;
    var best = double.infinity;
    for (var i = 0; i < ring.length - 1; i++) {
      best = math.min(best, _segmentMeters(ring[i], ring[i + 1], lat, lon));
    }
    return best;
  }

  static double _segmentMeters(List<double> a, List<double> b, double lat, double lon) {
    // Local flat-earth projection around the point: fine for a building plot.
    final k = math.cos(lat * math.pi / 180);
    const m = 111320.0;
    final ax = (a[0] - lon) * k * m, ay = (a[1] - lat) * m;
    final bx = (b[0] - lon) * k * m, by = (b[1] - lat) * m;
    final dx = bx - ax, dy = by - ay;
    final len2 = dx * dx + dy * dy;
    final t = len2 == 0 ? 0.0 : (-(ax * dx + ay * dy) / len2).clamp(0.0, 1.0);
    final px = ax + t * dx, py = ay + t * dy;
    return math.sqrt(px * px + py * py);
  }
}
