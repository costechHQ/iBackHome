import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/capture_rules.dart';
import '../core/geo.dart';
import '../core/location_tracker.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/site_map.dart';
import '../ui/states.dart';
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
  late LocationTracker _tracker = LocationTracker(widget.target.fence)..start();
  DateTime? _arrivedAt;

  @override
  void dispose() {
    _tracker.dispose();
    super.dispose();
  }

  /// "Check again": a fresh GPS stream and a fresh arrival time.
  void _again() {
    _tracker.dispose();
    setState(() {
      _arrivedAt = null;
      _tracker = LocationTracker(widget.target.fence)..start();
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Arrival check', subtitle: widget.target.subtitle ?? widget.target.title),
        body: ListenableBuilder(
          listenable: _tracker,
          builder: (context, _) {
            final r = _tracker.readiness;
            if (r.canShoot) _arrivedAt ??= DateTime.now();
            final (message, tone, icon) = switch (r.state) {
              Readiness.finding => ('Finding your location…', ChipTone.neutral, Icons.my_location),
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
              Readiness.ready => ('You\'re inside the site boundary.', ChipTone.ok, Icons.place_outlined),
              Readiness.readyOutside => (
                  'You\'re about ${r.distanceM.round()} m outside the site boundary. You can still capture, but the server will reject captures from here.',
                  ChipTone.warn,
                  Icons.warning_amber
                ),
              Readiness.readyNoSite => (
                  'This project has no site boundary yet, so captures will be flagged for operations to review.',
                  ChipTone.warn,
                  Icons.info_outline
                ),
            };
            final fix = _tracker.fix;
            final fence = widget.target.fence;
            // Inside: how far in from the edge (nearest edge, any side); outside: how far out.
            final edge = fence == null || fix == null ? null : Geo.distanceToEdge(fence, fix.latitude, fix.longitude);
            return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
              _Banner(_tracker.error ?? message, _tracker.error != null ? ChipTone.bad : tone, icon),
              if (widget.target.asContractor) ...[
                const SizedBox(height: IbhSpace.s12),
                const Alert('Uploaded by the contractor. This does not count toward supervisor verification.', tone: ChipTone.info),
              ],
              const SizedBox(height: IbhSpace.s16),
              SiteMap(ring: fence, lat: fix?.latitude, lon: fix?.longitude, accuracyM: fix?.accuracy),
              const SizedBox(height: IbhSpace.s16),
              IbhCard(
                child: Column(children: [
                  _kv('Distance to the boundary edge', edge == null ? '—' : (r.state == Readiness.readyOutside ? 'Outside, ${r.distanceM.round()} m' : 'Inside, ${edge.round()} m from the edge')),
                  _kv('GPS accuracy', r.accuracyM == null ? '—' : '±${r.accuracyM!.round()} m'),
                  _kv('Arrived', _arrivedAt == null ? '—' : watTime(_arrivedAt!)),
                ]),
              ),
              const SizedBox(height: IbhSpace.s12),
              Text('The phone only warns. The server checks every capture against the site boundary with a 25 m allowance.', style: IbhText.small.copyWith(color: IbhColors.muted)),
            ]);
          },
        ),
        bottomNavigationBar: ListenableBuilder(
          listenable: _tracker,
          builder: (context, _) {
            final r = _tracker.readiness;
            return BottomActionBar(children: [
              FilledButton(
                onPressed: r.canShoot
                    ? () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CaptureScreen(target: widget.target, tracker: _tracker)))
                    : null,
                child: Text(r.state == Readiness.readyOutside ? 'Capture anyway' : 'Start capturing'),
              ),
              OutlinedButton(onPressed: _again, child: const Text('Check again')),
            ]);
          },
        ),
      );

  static Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Text(k, style: IbhText.body.copyWith(color: IbhColors.muted))),
          const SizedBox(width: IbhSpace.s12),
          Flexible(child: Text(v, textAlign: TextAlign.right, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink))),
        ]),
      );
}

class _Banner extends StatelessWidget {
  const _Banner(this.text, this.tone, this.icon);
  final String text;
  final ChipTone tone;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (tone) {
      ChipTone.ok => (IbhColors.okBg, IbhColors.okFg),
      ChipTone.warn => (IbhColors.warnBg, IbhColors.warnFg),
      ChipTone.bad => (IbhColors.badBg, IbhColors.badFg),
      _ => (IbhColors.neutralBg, IbhColors.neutralFg),
    };
    return Container(
      padding: const EdgeInsets.all(IbhSpace.s12),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(IbhRadius.control)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: fg, size: 22),
        const SizedBox(width: IbhSpace.s12),
        Expanded(child: Text(text, style: TextStyle(color: fg, fontWeight: FontWeight.w700, fontSize: 15))),
      ]),
    );
  }
}
