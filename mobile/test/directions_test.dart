import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/geo.dart';

void main() {
  test('centroid of a square is its middle, ignoring the closing corner', () {
    final ring = [
      [7.0, 6.0],
      [7.2, 6.0],
      [7.2, 6.2],
      [7.0, 6.2],
      [7.0, 6.0],
    ];
    final (lat, lon) = Geo.centroid(ring);
    expect(lat, closeTo(6.1, 1e-9));
    expect(lon, closeTo(7.1, 1e-9));
  });

  test('centroid works without a closing corner', () {
    final (lat, lon) = Geo.centroid([
      [7.0, 6.0],
      [7.2, 6.0],
      [7.1, 6.3],
    ]);
    expect(lat, closeTo(6.1, 1e-9));
    expect(lon, closeTo(7.1, 1e-9));
  });
}
