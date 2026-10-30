import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

import '../core/geo.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'home_screen.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-005/006: arrival check and the in-app camera.
///
/// This is the only way evidence enters the app: there is no gallery picker anywhere. The
/// geofence banner is a warning only; the server makes the real decision.
class CaptureScreen extends ConsumerStatefulWidget {
  const CaptureScreen({
    super.key,
    required this.projectId,
    required this.milestoneId,
    required this.milestoneName,
    required this.fence,
    required this.asContractor,
  });

  final String projectId;
  final String milestoneId;
  final String milestoneName;
  final List<List<double>>? fence;
  final bool asContractor;

  @override
  ConsumerState<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends ConsumerState<CaptureScreen> {
  CameraController? _camera;
  StreamSubscription<Position>? _positions;
  Position? _fix;
  String? _problem;
  bool _busy = false;
  int _taken = 0;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    final cam = await Permission.camera.request();
    final loc = await Permission.locationWhenInUse.request();
    if (!cam.isGranted || !loc.isGranted) {
      setState(() => _problem = 'Camera and location permission are needed to capture evidence. '
          'Allow them in the phone settings.');
      return;
    }
    if (!await Geolocator.isLocationServiceEnabled()) {
      setState(() => _problem = 'Turn on the phone location (GPS) to capture evidence.');
      return;
    }
    try {
      final cameras = await availableCameras();
      final back = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back,
          orElse: () => cameras.first);
      final controller = CameraController(back, ResolutionPreset.high, enableAudio: false);
      await controller.initialize();
      _positions = Geolocator.getPositionStream(
        locationSettings: AndroidSettings(accuracy: LocationAccuracy.best, distanceFilter: 0),
      ).listen((p) => mounted ? setState(() => _fix = p) : null);
      if (mounted) setState(() => _camera = controller);
    } catch (e) {
      setState(() => _problem = 'The camera could not start: $e');
    }
  }

  @override
  void dispose() {
    _positions?.cancel();
    _camera?.dispose();
    super.dispose();
  }

  Future<void> _shoot() async {
    final fix = _fix;
    if (fix == null || _camera == null || _busy) return;
    setState(() => _busy = true);
    try {
      final deviceId = await ref.read(deviceProvider.future); // the key must be registered first
      final shutter = DateTime.now();
      final shot = await _camera!.takePicture();
      final raw = await shot.readAsBytes();
      final s = ref.read(servicesProvider);
      await s.capture.saveSignedPhoto(
        rawJpeg: raw,
        fix: fix,
        shutterTime: shutter,
        projectId: widget.projectId,
        milestoneId: widget.milestoneId,
        deviceId: deviceId,
      );
      setState(() => _taken++);
      unawaited(s.sync.syncNow());
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  ({String text, ChipTone tone}) get _arrival {
    final fix = _fix;
    if (fix == null) return (text: 'Waiting for a GPS fix...', tone: ChipTone.neutral);
    final fence = widget.fence;
    if (fence == null) return (text: 'No site boundary set; the server will flag this capture.', tone: ChipTone.warn);
    final d = Geo.distanceToFence(fence, fix.latitude, fix.longitude);
    final acc = '±${fix.accuracy.round()} m';
    if (d == 0) return (text: 'You are inside the site ($acc).', tone: ChipTone.ok);
    if (d <= 25) return (text: 'Just outside the boundary, within the 25 m allowance ($acc).', tone: ChipTone.warn);
    return (text: 'You are about ${d.round()} m outside the site. The server will reject captures from here.', tone: ChipTone.bad);
  }

  @override
  Widget build(BuildContext context) {
    final camera = _camera;
    final arrival = _arrival;
    return Scaffold(
      backgroundColor: IbhColors.camera,
      appBar: AppBar(title: Text(widget.milestoneName)),
      body: _problem != null
          ? Padding(padding: const EdgeInsets.all(IbhSpace.s24), child: Alert(_problem!, tone: ChipTone.bad))
          : camera == null
              ? const Center(child: CircularProgressIndicator())
              : Column(children: [
                  Padding(
                    padding: const EdgeInsets.all(IbhSpace.s12),
                    child: Alert(arrival.text, tone: arrival.tone),
                  ),
                  if (widget.asContractor)
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: IbhSpace.s12),
                      child: Alert('Contractor evidence is labelled as yours and does not count toward verification.',
                          tone: ChipTone.info),
                    ),
                  Expanded(child: Center(child: CameraPreview(camera))),
                  Padding(
                    padding: const EdgeInsets.all(IbhSpace.s16),
                    child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Text('$_taken taken', style: const TextStyle(color: IbhColors.white)),
                      const SizedBox(width: IbhSpace.s24),
                      SizedBox(
                        width: 72,
                        height: 72,
                        child: FilledButton(
                          style: FilledButton.styleFrom(shape: const CircleBorder(), padding: EdgeInsets.zero),
                          onPressed: _fix == null || _busy ? null : _shoot,
                          child: _busy
                              ? const CircularProgressIndicator(color: IbhColors.white)
                              : const Icon(Icons.camera_alt, size: 32),
                        ),
                      ),
                    ]),
                  ),
                ]),
    );
  }
}
