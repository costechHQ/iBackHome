import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart' show Position;

import '../core/capture_rules.dart';
import '../core/capture_service.dart';
import '../core/location_tracker.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'capture_target.dart';
import 'home_screen.dart';
import 'review_screen.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-006: the in-app camera.
///
/// There is no gallery or file picker anywhere in the app. The shutter is refused for weak GPS
/// or a mock location; outside the boundary the app warns but allows the shot (the server rejects).
class CaptureScreen extends ConsumerStatefulWidget {
  const CaptureScreen({super.key, required this.target, required this.tracker});

  final CaptureTarget target;
  final LocationTracker tracker;

  @override
  ConsumerState<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends ConsumerState<CaptureScreen> {
  CameraController? _camera;
  String? _problem;
  bool _busy = false;
  int _kept = 0;
  bool _video = false;
  bool _recording = false;
  int _seconds = 0;
  Timer? _timer;
  DateTime? _recordStart;
  Position? _recordFix;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      final back = cameras.firstWhere((c) => c.lensDirection == CameraLensDirection.back,
          orElse: () => cameras.first);
      final controller = CameraController(back, ResolutionPreset.high, enableAudio: false);
      await controller.initialize();
      if (mounted) setState(() => _camera = controller);
    } catch (e) {
      if (mounted) setState(() => _problem = 'The camera could not start. Close other camera apps and try again.');
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _camera?.dispose();
    super.dispose();
  }

  /// Video: the GPS fix and clock are read when recording starts, and signed with the file.
  /// Recording stops by itself at 60 seconds.
  Future<void> _toggleRecording() async {
    final cam = _camera;
    if (cam == null || _busy) return;
    if (!_recording) {
      final fix = widget.tracker.fix;
      if (fix == null || !widget.tracker.readiness.canShoot) return;
      try {
        await cam.startVideoRecording();
      } catch (e) {
        if (mounted) showError(context, 'Recording could not start.');
        return;
      }
      _recordFix = fix;
      _recordStart = DateTime.now();
      _seconds = 0;
      _timer = Timer.periodic(const Duration(seconds: 1), (t) {
        setState(() => _seconds++);
        if (_seconds >= CaptureService.maxVideoSeconds) unawaited(_toggleRecording());
      });
      setState(() => _recording = true);
      return;
    }
    _timer?.cancel();
    setState(() {
      _recording = false;
      _busy = true;
    });
    try {
      final file = await cam.stopVideoRecording();
      final deviceId = await ref.read(deviceProvider.future);
      final s = ref.read(servicesProvider);
      final draft = await s.capture.saveSignedVideo(
        recorded: File(file.path),
        fix: _recordFix!,
        shutterTime: _recordStart!,
        projectId: widget.target.projectId,
        milestoneId: widget.target.milestoneId,
        deviceId: deviceId,
        contextRef: widget.target.contextRef,
        asContractor: widget.target.asContractor,
      );
      if (!mounted) return;
      final kept = await Navigator.of(context).push<bool>(
          MaterialPageRoute(builder: (_) => ReviewScreen(capture: draft, target: widget.target)));
      if (kept == true) {
        setState(() => _kept++);
        unawaited(s.sync.syncNow());
      }
    } catch (e) {
      if (mounted) showError(context, e is StateError ? e.message : e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _shoot() async {
    final fix = widget.tracker.fix;
    if (fix == null || _camera == null || _busy || !widget.tracker.readiness.canShoot) return;
    setState(() => _busy = true);
    try {
      final deviceId = await ref.read(deviceProvider.future); // the key must be registered first
      final shutter = DateTime.now();
      final shot = await _camera!.takePicture();
      final raw = await shot.readAsBytes();
      final s = ref.read(servicesProvider);
      final draft = await s.capture.saveSignedPhoto(
        rawJpeg: raw,
        fix: fix,
        shutterTime: shutter,
        projectId: widget.target.projectId,
        milestoneId: widget.target.milestoneId,
        deviceId: deviceId,
        contextRef: widget.target.contextRef,
        asContractor: widget.target.asContractor,
      );
      if (!mounted) return;
      final kept = await Navigator.of(context).push<bool>(MaterialPageRoute(
          builder: (_) => ReviewScreen(capture: draft, target: widget.target)));
      if (kept == true) {
        setState(() => _kept++);
        unawaited(s.sync.syncNow());
      }
    } catch (e) {
      if (mounted) showError(context, e is StateError ? e.message : e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final camera = _camera;
    return Scaffold(
      backgroundColor: IbhColors.camera,
      appBar: AppBar(title: Text(widget.target.title, overflow: TextOverflow.ellipsis)),
      body: _problem != null
          ? Padding(padding: const EdgeInsets.all(IbhSpace.s24), child: Alert(_problem!, tone: ChipTone.bad))
          : camera == null
              ? const Center(child: CircularProgressIndicator())
              : ListenableBuilder(
                  listenable: widget.tracker,
                  builder: (context, _) {
                    final r = widget.tracker.readiness;
                    return Column(children: [
                      Padding(padding: const EdgeInsets.all(IbhSpace.s12), child: _banner(r)),
                      Expanded(child: Center(child: CameraPreview(camera))),
                      Padding(
                        padding: const EdgeInsets.all(IbhSpace.s16),
                        child: Column(children: [
                          if (!_recording)
                            SegmentedButton<bool>(
                              segments: const [
                                ButtonSegment(value: false, icon: Icon(Icons.photo_camera), label: Text('Photo')),
                                ButtonSegment(value: true, icon: Icon(Icons.videocam), label: Text('Video')),
                              ],
                              selected: {_video},
                              onSelectionChanged: (s) => setState(() => _video = s.first),
                            )
                          else
                            Text('Recording ${_seconds}s of ${CaptureService.maxVideoSeconds}s',
                                style: const TextStyle(color: IbhColors.badOnDark, fontWeight: FontWeight.w600)),
                          const SizedBox(height: IbhSpace.s12),
                          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                            Text('$_kept saved', style: const TextStyle(color: IbhColors.white)),
                            const SizedBox(width: IbhSpace.s24),
                            Semantics(
                              button: true,
                              label: _video ? (_recording ? 'Stop recording' : 'Start recording') : 'Take photo',
                              child: SizedBox(
                                width: 72,
                                height: 72,
                                child: FilledButton(
                                  style: FilledButton.styleFrom(
                                    shape: const CircleBorder(),
                                    padding: EdgeInsets.zero,
                                    backgroundColor: _recording ? IbhColors.badFg : null,
                                  ),
                                  onPressed: (r.canShoot || _recording) && !_busy
                                      ? (_video ? _toggleRecording : _shoot)
                                      : null,
                                  child: _busy
                                      ? const CircularProgressIndicator(color: IbhColors.white)
                                      : Icon(_video ? (_recording ? Icons.stop : Icons.fiber_manual_record) : Icons.camera_alt,
                                          size: 32),
                                ),
                              ),
                            ),
                          ]),
                        ]),
                      ),
                    ]);
                  },
                ),
    );
  }

  Widget _banner(CaptureReadiness r) {
    final (text, tone) = switch (r.state) {
      Readiness.finding => ('Waiting for a GPS fix...', ChipTone.neutral),
      Readiness.weakGps => ('GPS too weak (±${r.accuracyM?.round()} m). Capture needs ±50 m or better.', ChipTone.bad),
      Readiness.mockLocation => ('Simulated location detected. Capture is blocked.', ChipTone.bad),
      Readiness.ready => ('At the site (±${r.accuracyM?.round()} m).', ChipTone.ok),
      Readiness.readyOutside => (
          'About ${r.distanceM.round()} m outside the site. The server will reject this capture.',
          ChipTone.warn
        ),
      Readiness.readyNoSite => ('No site boundary yet: ops will review this capture.', ChipTone.warn),
    };
    return Column(children: [
      Alert(text, tone: tone),
      if (widget.target.asContractor) ...[
        const SizedBox(height: IbhSpace.s8),
        const Alert('Uploaded by the contractor: does not count toward verification.', tone: ChipTone.info),
      ],
    ]);
  }
}

/// Small helper for screens that list a capture's thumbnail status.
String captureStatusLabel(String status) => switch (status) {
      CaptureStatus.accepted => 'Accepted',
      CaptureStatus.flagged => 'Flagged for review',
      CaptureStatus.rejected => 'Rejected',
      CaptureStatus.failed => 'Needs attention',
      CaptureStatus.submitted => 'Server checking',
      CaptureStatus.draft => 'Not saved yet',
      _ => 'Waiting to upload',
    };
