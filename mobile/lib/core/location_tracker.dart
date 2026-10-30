import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

import 'capture_rules.dart';

/// One live GPS stream shared by the arrival check and the camera.
class LocationTracker extends ChangeNotifier {
  LocationTracker(this.fence);

  final List<List<double>>? fence;
  StreamSubscription<Position>? _sub;
  Position? fix;
  String? error;

  CaptureReadiness get readiness => assessReadiness(
        lat: fix?.latitude,
        lon: fix?.longitude,
        accuracyM: fix?.accuracy,
        mocked: fix?.isMocked ?? false,
        fence: fence,
      );

  void start() {
    _sub = Geolocator.getPositionStream(
      locationSettings: AndroidSettings(accuracy: LocationAccuracy.best, distanceFilter: 0),
    ).listen((p) {
      fix = p;
      error = null;
      notifyListeners();
    }, onError: (Object e) {
      error = 'The phone could not read its location.';
      notifyListeners();
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
