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
import '../ui/ibh_app_bar.dart';
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
    final device = ref.watch(deviceProvider);
    return Scaffold(
      appBar: IbhAppBar(title: 'Capture', subtitle: widget.target.title, leading: IbhBarLeading.close),
      body: _problem != null
          ? Padding(padding: const EdgeInsets.all(IbhSpace.s24), child: Alert(_problem!, tone: ChipTone.bad))
          : camera == null
              ? const Center(child: CircularProgressIndicator())
              : ListenableBuilder(
                  listenable: widget.tracker,
                  builder: (context, _) {
                    final r = widget.tracker.readiness;
                    return Column(children: [
                      Padding(padding: const EdgeInsets.fromLTRB(IbhSpace.s16, IbhSpace.s12, IbhSpace.s16, IbhSpace.s8), child: _banner(r)),
                      _pills(r, device),
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.all(IbhSpace.s16),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(IbhRadius.card),
                            child: ColoredBox(
                              color: IbhColors.camera,
                              child: Stack(fit: StackFit.expand, children: [
                                FittedBox(
                                  fit: BoxFit.cover,
                                  clipBehavior: Clip.hardEdge,
                                  child: SizedBox(
                                    width: camera.value.previewSize?.height ?? 1,
                                    height: camera.value.previewSize?.width ?? 1,
                                    child: CameraPreview(camera),
                                  ),
                                ),
                                if (_recording)
                                  Positioned(
                                    top: 12,
                                    left: 12,
                                    child: StatusChip('Recording ${_seconds}s of ${CaptureService.maxVideoSeconds}s', tone: ChipTone.bad),
                                  ),
                                if (widget.target.asContractor)
                                  const Positioned(top: 12, right: 12, child: StatusChip('Contractor evidence', tone: ChipTone.info)),
                              ]),
                            ),
                          ),
                        ),
                      ),
                      if (widget.target.asContractor)
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: IbhSpace.s16),
                          child: Alert('Uploaded by the contractor: does not count toward verification.', tone: ChipTone.info),
                        ),
                      _modeSwitch(),
                      _shutter(r),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(IbhSpace.s16, IbhSpace.s4, IbhSpace.s16, IbhSpace.s16),
                        child: Text(
                          _kept == 0 ? "In-app camera only. There's no gallery or file picker." : "$_kept saved · In-app camera only. There's no gallery or file picker.",
                          textAlign: TextAlign.center,
                          style: IbhText.small.copyWith(color: IbhColors.muted),
                        ),
                      ),
                    ]);
                  },
                ),
    );
  }

  Widget _modeSwitch() {
    Widget seg(String label, bool video) {
      final on = _video == video;
      return Semantics(
        button: true,
        selected: on,
        child: InkWell(
          borderRadius: BorderRadius.circular(IbhRadius.control),
          onTap: _recording ? null : () => setState(() => _video = video),
          child: Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s20),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: on ? IbhColors.white : Colors.transparent,
              borderRadius: BorderRadius.circular(IbhRadius.control),
              border: on ? Border.all(color: IbhColors.frame) : null,
            ),
            child: Text(label, style: TextStyle(fontWeight: FontWeight.w700, color: on ? IbhColors.ink : IbhColors.muted)),
          ),
        ),
      );
    }

    return Row(mainAxisAlignment: MainAxisAlignment.center, children: [seg('Photo', false), const SizedBox(width: IbhSpace.s8), seg('Video · 60 s max', true)]);
  }

  /// The ring shutter from the design: a navy disc inside a navy ring (red while recording).
  Widget _shutter(CaptureReadiness r) {
    final enabled = (r.canShoot || _recording) && !_busy;
    final colour = _recording ? IbhColors.badFg : IbhColors.navy900;
    return Padding(
      padding: const EdgeInsets.only(top: IbhSpace.s8),
      child: Semantics(
        button: true,
        enabled: enabled,
        label: _video ? (_recording ? 'Stop recording' : 'Start recording') : 'Take photo',
        child: GestureDetector(
          onTap: enabled ? (_video ? _toggleRecording : _shoot) : null,
          child: Opacity(
            opacity: enabled ? 1 : 0.4,
            child: Container(
              width: 76,
              height: 76,
              alignment: Alignment.center,
              decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: colour, width: 4), color: IbhColors.white),
              child: _busy
                  ? const SizedBox(height: 28, width: 28, child: CircularProgressIndicator(strokeWidth: 3))
                  : Container(
                      width: _recording ? 28 : 56,
                      height: _recording ? 28 : 56,
                      decoration: BoxDecoration(color: colour, shape: _recording ? BoxShape.rectangle : BoxShape.circle, borderRadius: _recording ? BorderRadius.circular(6) : null),
                    ),
            ),
          ),
        ),
      ),
    );
  }

  /// GPS accuracy, the device key and the clock, as the design's three small pills.
  Widget _pills(CaptureReadiness r, AsyncValue<String> device) {
    final fix = widget.tracker.fix;
    final drift = fix == null ? null : DateTime.now().difference(fix.timestamp).abs();
    final clockOk = drift == null || drift < const Duration(minutes: 10);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s16),
      child: Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
        StatusChip(r.accuracyM == null ? 'GPS searching' : 'GPS ±${r.accuracyM!.round()} m',
            tone: r.state == Readiness.weakGps ? ChipTone.bad : (r.accuracyM == null ? ChipTone.neutral : ChipTone.ok)),
        StatusChip(device.hasValue ? 'Device key ready' : (device.hasError ? 'Device key missing' : 'Device key…'),
            tone: device.hasValue ? ChipTone.ok : (device.hasError ? ChipTone.bad : ChipTone.neutral)),
        StatusChip(clockOk ? 'Clock OK' : 'Clock off by ${drift.inMinutes} min', tone: clockOk ? ChipTone.ok : ChipTone.warn),
      ]),
    );
  }

  Widget _banner(CaptureReadiness r) {
    final (text, tone, icon) = switch (r.state) {
      Readiness.finding => ('Waiting for a GPS fix…', ChipTone.neutral, Icons.my_location),
      Readiness.weakGps => ('GPS too weak (±${r.accuracyM?.round()} m). Capture needs ±50 m or better.', ChipTone.bad, Icons.gps_off),
      Readiness.mockLocation => ('Simulated location detected. Capture is blocked.', ChipTone.bad, Icons.location_disabled),
      Readiness.ready => ('Inside site boundary · GPS ±${r.accuracyM?.round()} m', ChipTone.ok, Icons.place_outlined),
      Readiness.readyOutside => ('About ${r.distanceM.round()} m outside the site. The server will reject this capture.', ChipTone.warn, Icons.warning_amber),
      Readiness.readyNoSite => ('No site boundary yet: ops will review this capture.', ChipTone.warn, Icons.info_outline),
    };
    final (bg, fg) = switch (tone) {
      ChipTone.ok => (IbhColors.okBg, IbhColors.okFg),
      ChipTone.warn => (IbhColors.warnBg, IbhColors.warnFg),
      ChipTone.bad => (IbhColors.badBg, IbhColors.badFg),
      _ => (IbhColors.neutralBg, IbhColors.neutralFg),
    };
    return Container(
      padding: const EdgeInsets.all(IbhSpace.s12),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(IbhRadius.control)),
      child: Row(children: [
        Icon(icon, color: fg, size: 22),
        const SizedBox(width: IbhSpace.s12),
        Expanded(child: Text(text, style: TextStyle(color: fg, fontWeight: FontWeight.w700, fontSize: 15))),
      ]),
    );
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
