import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/signing.dart';

void main() {
  // The vector from backend/app/features/evidence/SIGNING.md: Dart must build the same bytes.
  test('payload matches the backend test vector', () {
    final bytes = EvidencePayload.build(
      fileSha256: 'a' * 64,
      capturedAt: DateTime.utc(2026, 10, 12, 9, 30, 15, 123),
      gpsTime: DateTime.utc(2026, 10, 12, 9, 30, 14, 900),
      lat: 6.4595,
      lon: 7.50045,
      accuracyM: 8.5,
      projectId: '11111111-2222-3333-4444-555555555555',
      deviceId: 'device-abc',
    );
    expect(
      utf8.decode(bytes),
      'ibh-evidence-v1|${'a' * 64}|2026-10-12T09:30:15.123Z|2026-10-12T09:30:14.900Z|'
      '6.459500|7.500450|8.5|11111111-2222-3333-4444-555555555555|device-abc',
    );
  });

  test('negative zero is written as zero', () {
    expect(EvidencePayload.fixed(-0.0000001, 6), '0.000000');
    expect(EvidencePayload.fixed(-6.4595, 6), '-6.459500');
  });

  test('rounding matches what is sent to the server', () {
    expect(EvidencePayload.round(6.45950049, 6), 6.4595);
    expect(EvidencePayload.round(8.46, 1), 8.5);
  });

  test('timestamps are UTC with milliseconds', () {
    expect(EvidencePayload.utcText(DateTime.utc(2026, 1, 2, 3, 4, 5)), '2026-01-02T03:04:05.000Z');
  });

  test('a bad hash or device id is refused', () {
    final base = {
      'capturedAt': DateTime.utc(2026),
      'gpsTime': DateTime.utc(2026),
    };
    expect(
      () => EvidencePayload.build(
          fileSha256: 'XYZ',
          capturedAt: base['capturedAt']!,
          gpsTime: base['gpsTime']!,
          lat: 0,
          lon: 0,
          accuracyM: 1,
          projectId: 'p',
          deviceId: 'd'),
      throwsArgumentError,
    );
    expect(
      () => EvidencePayload.build(
          fileSha256: 'a' * 64,
          capturedAt: base['capturedAt']!,
          gpsTime: base['gpsTime']!,
          lat: 0,
          lon: 0,
          accuracyM: 1,
          projectId: 'p',
          deviceId: 'a|b'),
      throwsArgumentError,
    );
  });
}
