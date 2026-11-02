import 'package:flutter/services.dart';

/// How much room the phone has left, from Android's `StatFs` (`MainActivity.kt`).
///
/// Below [warnBytes] the Me tab shows the "storage almost full" alert; below [stopBytes] the camera
/// refuses to capture, because a photo that can't be saved is worse than no photo.
class FreeSpace {
  FreeSpace._();

  static const warnBytes = 250 * 1024 * 1024;
  static const stopBytes = 100 * 1024 * 1024;

  static const _channel = MethodChannel('ng.ibackhome/storage');

  /// Free bytes in the app's storage, or null if the phone can't say (never blocks capture).
  static Future<int?> freeBytes() async {
    try {
      return await _channel.invokeMethod<int>('freeBytes');
    } catch (_) {
      return null;
    }
  }

  static StorageLevel level(int? free) {
    if (free == null) return StorageLevel.ok;
    if (free < stopBytes) return StorageLevel.full;
    if (free < warnBytes) return StorageLevel.low;
    return StorageLevel.ok;
  }
}

enum StorageLevel { ok, low, full }
