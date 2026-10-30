import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image/image.dart' as img;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import 'capture_rules.dart';
import 'queue_db.dart';
import 'signing.dart';

/// Turns a camera frame into a signed capture.
///
/// Order matters (SIGNING.md): compress first, hash the exact bytes that will be uploaded, sign
/// that hash with the GPS stamp, and only then store. No gallery or file-picker code exists.
/// The capture is stored as a `draft` until the supervisor keeps it in the review step.
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

  /// Refuses what the design says the app must refuse; the server still checks everything again.
  static void ensureAllowed(Position fix) {
    if (fix.isMocked) {
      throw StateError('Location looks simulated. Turn off mock locations and try again.');
    }
    if (fix.accuracy > maxAccuracyM) {
      throw StateError('GPS is too weak (±${fix.accuracy.round()} m). Move to open sky and try again.');
    }
  }

  /// [shutterTime] is the phone's clock at the shutter; [fix] the GPS reading taken with it.
  Future<QueuedCapture> saveSignedPhoto({
    required Uint8List rawJpeg,
    required Position fix,
    required DateTime shutterTime,
    required String projectId,
    String? milestoneId,
    required String deviceId,
    String? contextRef,
    bool asContractor = false,
  }) async {
    ensureAllowed(fix);
    final bytes = await compute(compress, rawJpeg);
    final dir = await _capturesDir();
    final id = const Uuid().v4();
    final file = File(p.join(dir.path, '$id.jpg'));
    await file.writeAsBytes(bytes, flush: true);
    return _signAndStore(
      id: id,
      file: file,
      sha: sha256.convert(bytes).toString(),
      kind: 'photo',
      fix: fix,
      shutterTime: shutterTime,
      projectId: projectId,
      milestoneId: milestoneId,
      deviceId: deviceId,
      contextRef: contextRef,
      asContractor: asContractor,
    );
  }

  /// Videos are signed as recorded (MP4, up to 60 s at 720p); there is no re-encoding step, so
  /// the hash is taken over the recorded file itself. [shutterTime] and [fix] are from the moment
  /// recording started.
  Future<QueuedCapture> saveSignedVideo({
    required File recorded,
    required Position fix,
    required DateTime shutterTime,
    required String projectId,
    String? milestoneId,
    required String deviceId,
    String? contextRef,
    bool asContractor = false,
  }) async {
    ensureAllowed(fix);
    final id = const Uuid().v4();
    final dir = await _capturesDir();
    final file = await recorded.copy(p.join(dir.path, '$id.mp4'));
    await recorded.delete();
    if (await file.length() > maxVideoBytes) {
      await file.delete();
      throw StateError('That video is too large to upload (limit 60 MB). Record a shorter one.');
    }
    final sha = (await sha256.bind(file.openRead()).first).toString();
    return _signAndStore(
      id: id,
      file: file,
      sha: sha,
      kind: 'video',
      fix: fix,
      shutterTime: shutterTime,
      projectId: projectId,
      milestoneId: milestoneId,
      deviceId: deviceId,
      contextRef: contextRef,
      asContractor: asContractor,
    );
  }

  /// The server accepts videos up to 60 MB and photos up to 10 MB.
  static const maxVideoBytes = 60 * 1024 * 1024;
  static const maxVideoSeconds = 60;

  Future<Directory> _capturesDir() async {
    final dir = Directory(p.join((await getApplicationDocumentsDirectory()).path, 'captures'));
    await dir.create(recursive: true);
    return dir;
  }

  Future<QueuedCapture> _signAndStore({
    required String id,
    required File file,
    required String sha,
    required String kind,
    required Position fix,
    required DateTime shutterTime,
    required String projectId,
    String? milestoneId,
    required String deviceId,
    String? contextRef,
    bool asContractor = false,
  }) async {
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

    final capture = QueuedCapture(
      id: id,
      projectId: projectId,
      milestoneId: milestoneId,
      kind: kind,
      filePath: file.path,
      sha256: sha,
      capturedAt: capturedAt,
      gpsTime: gpsTime,
      lat: lat,
      lon: lon,
      accuracyM: acc,
      deviceId: deviceId,
      signature: signature,
      status: CaptureStatus.draft,
      contextRef: contextRef,
      asContractor: asContractor,
    );
    await _db.insert(capture);
    return capture;
  }
}
