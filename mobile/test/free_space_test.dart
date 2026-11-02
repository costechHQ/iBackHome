import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/free_space.dart';

void main() {
  const mb = 1024 * 1024;

  test('plenty of room is fine, and an unknown reading never blocks capture', () {
    expect(FreeSpace.level(500 * mb), StorageLevel.ok);
    expect(FreeSpace.level(null), StorageLevel.ok);
  });

  test('below 250 MB warns, below 100 MB stops the camera', () {
    expect(FreeSpace.level(180 * mb), StorageLevel.low);
    expect(FreeSpace.level(250 * mb), StorageLevel.ok);
    expect(FreeSpace.level(99 * mb), StorageLevel.full);
    expect(FreeSpace.level(100 * mb), StorageLevel.low);
  });
}
