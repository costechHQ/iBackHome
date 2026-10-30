import 'dart:convert';

import 'package:flutter/services.dart';

/// The exact bytes the phone signs. Contract: backend/app/features/evidence/SIGNING.md
/// (`ibh-evidence-v1|sha256|captured_at|gps_time|lat|lon|accuracy|project_id|device_id`).
/// Change this and the backend's `signing.py` together; `test/signing_test.dart` pins the vector.
class EvidencePayload {
  EvidencePayload._();

  static const version = 'ibh-evidence-v1';

  static String utcText(DateTime moment) {
    final u = moment.toUtc();
    String p(int n, int w) => n.toString().padLeft(w, '0');
    return '${p(u.year, 4)}-${p(u.month, 2)}-${p(u.day, 2)}T'
        '${p(u.hour, 2)}:${p(u.minute, 2)}:${p(u.second, 2)}.${p(u.millisecond, 3)}Z';
  }

  /// Fixed decimals, never "-0.000000".
  static String fixed(double value, int places) {
    final text = value.toStringAsFixed(places);
    return text.startsWith('-') && double.parse(text) == 0 ? text.substring(1) : text;
  }

  static double round(double value, int places) => double.parse(fixed(value, places));

  static List<int> build({
    required String fileSha256,
    required DateTime capturedAt,
    required DateTime gpsTime,
    required double lat,
    required double lon,
    required double accuracyM,
    required String projectId,
    required String deviceId,
  }) {
    if (!RegExp(r'^[0-9a-f]{64}$').hasMatch(fileSha256)) {
      throw ArgumentError('file_sha256 must be 64 lowercase hex characters');
    }
    if (deviceId.isEmpty || deviceId.contains('|') || deviceId.contains(RegExp(r'[\r\n]'))) {
      throw ArgumentError('device_id must not contain "|" or line breaks');
    }
    return utf8.encode([
      version,
      fileSha256,
      utcText(capturedAt),
      utcText(gpsTime),
      fixed(lat, 6),
      fixed(lon, 6),
      fixed(accuracyM, 1),
      projectId.toLowerCase(),
      deviceId,
    ].join('|'));
  }
}

/// The ECDSA P-256 key in the Android Keystore (see MainActivity.kt). The private key never
/// reaches Dart; this only asks the platform to sign.
class Keystore {
  Keystore(this.alias);

  static const _channel = MethodChannel('ng.ibackhome/keystore');
  final String alias;

  /// Creates the key if needed; returns base64 X.509 SubjectPublicKeyInfo DER.
  Future<String> ensureKey() async =>
      (await _channel.invokeMethod<String>('ensureKey', {'alias': alias}))!;

  /// Returns the base64 DER ECDSA/SHA-256 signature of [data].
  Future<String> sign(List<int> data) async => (await _channel.invokeMethod<String>(
      'sign', {'alias': alias, 'data': Uint8List.fromList(data)}))!;

  Future<void> deleteKey() => _channel.invokeMethod<void>('deleteKey', {'alias': alias});
}
