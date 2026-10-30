import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image/image.dart' as img;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import 'queue_db.dart';
import 'signing.dart';

/// Turns a camera frame into a signed, queued capture.
///
/// Order matters (SIGNING.md): compress first, hash the exact bytes that will be uploaded, sign
/// that hash with the GPS stamp, and only then store. No gallery or file-picker code exists.
class CaptureService {
  CaptureService(this._db, this._keystore);

  final QueueDb _db;
  final Keystore _keystore;

  /// ~1600 px on the long side, JPEG quality 80. Re-encoding also drops EXIF.
  static Uint8List compress(Uint8List raw) {
    var image = img.decodeImage(raw);
    if (image == null) throw const FormatException('The camera frame could not be read.');
    image = img.bakeOrientation(image);
    const maxSide = 1600;
    if (image.width > maxSide || image.height > maxSide) {
      image = image.width >= image.height
          ? img.copyResize(image, width: maxSide)
          : img.copyResize(image, height: maxSide);
    }
    return Uint8List.fromList(img.encodeJpg(image, quality: 80));
  }

  /// [shutterTime] is the phone's clock at the shutter; [fix] the GPS reading taken with it.
  Future<QueuedCapture> saveSignedPhoto({
    required Uint8List rawJpeg,
    required Position fix,
    required DateTime shutterTime,
    required String projectId,
    String? milestoneId,
    required String deviceId,
  }) async {
    if (fix.isMocked) {
      throw StateError('Location looks simulated. Turn off mock locations and try again.');
    }
    final bytes = await compute(compress, rawJpeg);
    final sha = sha256.convert(bytes).toString();
    final lat = EvidencePayload.round(fix.latitude, 6);
    final lon = EvidencePayload.round(fix.longitude, 6);
    final acc = EvidencePayload.round(fix.accuracy, 1);
    final capturedAt = DateTime.fromMillisecondsSinceEpoch(shutterTime.millisecondsSinceEpoch, isUtc: true);
    final gpsTime = DateTime.fromMillisecondsSinceEpoch(fix.timestamp.millisecondsSinceEpoch, isUtc: true);

    final signature = await _keystore.sign(EvidencePayload.build(
      fileSha256: sha,
      capturedAt: capturedAt,
      gpsTime: gpsTime,
      lat: lat,
      lon: lon,
      accuracyM: acc,
      projectId: projectId,
      deviceId: deviceId,
    ));

    final id = const Uuid().v4();
    final dir = Directory(p.join((await getApplicationDocumentsDirectory()).path, 'captures'));
    await dir.create(recursive: true);
    final file = File(p.join(dir.path, '$id.jpg'));
    await file.writeAsBytes(bytes, flush: true);

    final capture = QueuedCapture(
      id: id,
      projectId: projectId,
      milestoneId: milestoneId,
      kind: 'photo',
      filePath: file.path,
      sha256: sha,
      capturedAt: capturedAt,
      gpsTime: gpsTime,
      lat: lat,
      lon: lon,
      accuracyM: acc,
      deviceId: deviceId,
      signature: signature,
    );
    await _db.insert(capture);
    return capture;
  }
}
