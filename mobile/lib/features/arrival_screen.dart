import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/capture_rules.dart';
import '../core/location_tracker.dart';
import '../theme/ibh_tokens.dart';
import 'capture_screen.dart';
import 'capture_target.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-005: find the phone's location and say whether it is inside the site.
/// A warning only; the server decides.
class ArrivalScreen extends ConsumerStatefulWidget {
  const ArrivalScreen({super.key, required this.target});
  final CaptureTarget target;

  @override
  ConsumerState<ArrivalScreen> createState() => _ArrivalScreenState();
}

class _ArrivalScreenState extends ConsumerState<ArrivalScreen> {
  late final LocationTracker _tracker = LocationTracker(widget.target.fence)..start();

  @override
  void dispose() {
    _tracker.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Arrival check')),
        body: ListenableBuilder(
          listenable: _tracker,
          builder: (context, _) {
            final r = _tracker.readiness;
            final (message, tone, icon) = switch (r.state) {
              Readiness.finding => ('Finding your location...', ChipTone.neutral, Icons.my_location),
              Readiness.weakGps => (
                  'GPS is too weak (±${r.accuracyM?.round()} m). Move to open sky; capture needs ±50 m or better.',
                  ChipTone.bad,
                  Icons.gps_off
                ),
              Readiness.mockLocation => (
                  'This phone reports a simulated location. Turn off mock locations to capture.',
                  ChipTone.bad,
                  Icons.location_disabled
                ),
              Readiness.ready => (
                  'You are at the site (±${r.accuracyM?.round()} m).',
                  ChipTone.ok,
                  Icons.check_circle_outline
                ),
              Readiness.readyOutside => (
                  'You are about ${r.distanceM.round()} m outside the site boundary. You can still capture, but the '
                      'server will reject captures from here.',
                  ChipTone.warn,
                  Icons.warning_amber
                ),
              Readiness.readyNoSite => (
                  'This project has no site boundary yet, so captures will be flagged for operations to review.',
                  ChipTone.warn,
                  Icons.info_outline
                ),
            };
            return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
              Text(widget.target.title, style: IbhText.h3),
              const SizedBox(height: IbhSpace.s24),
              Center(child: Icon(icon, size: 72, color: IbhColors.navy900)),
              const SizedBox(height: IbhSpace.s16),
              if (_tracker.error != null) Alert(_tracker.error!, tone: ChipTone.bad) else Alert(message, tone: tone),
              if (widget.target.asContractor) ...[
                const SizedBox(height: IbhSpace.s12),
                const Alert('Uploaded by the contractor. This does not count toward supervisor verification.',
                    tone: ChipTone.info),
              ],
              const SizedBox(height: IbhSpace.s24),
              FilledButton(
                onPressed: r.canShoot
                    ? () => Navigator.of(context).push(MaterialPageRoute<void>(
                        builder: (_) => CaptureScreen(target: widget.target, tracker: _tracker)))
                    : null,
                child: Text(r.state == Readiness.readyOutside ? 'Capture anyway' : 'Start capturing'),
              ),
            ]);
          },
        ),
      );
}
