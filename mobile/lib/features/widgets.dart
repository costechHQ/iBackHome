import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/capture_rules.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';

/// Chip colours follow the design system: status colours only in chips and alerts.
class StatusChip extends StatelessWidget {
  const StatusChip(this.label, {super.key, this.tone = ChipTone.neutral});

  final String label;
  final ChipTone tone;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (tone) {
      ChipTone.ok => (IbhColors.okBg, IbhColors.okFg),
      ChipTone.warn => (IbhColors.warnBg, IbhColors.warnFg),
      ChipTone.bad => (IbhColors.badBg, IbhColors.badFg),
      ChipTone.info => (IbhColors.infoBg, IbhColors.infoFg),
      ChipTone.neutral => (IbhColors.neutralBg, IbhColors.neutralFg),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(IbhRadius.pill)),
      child: Text(label,
          style: TextStyle(color: fg, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}

enum ChipTone { ok, warn, bad, info, neutral }

ChipTone milestoneTone(String status) => switch (status) {
      'released' || 'approved' || 'verified' => ChipTone.ok,
      'claimed' => ChipTone.info,
      'disputed' => ChipTone.bad,
      'funded' => ChipTone.warn,
      _ => ChipTone.neutral,
    };

/// An inline alert box (warn / bad / info) with the design system colours.
class Alert extends StatelessWidget {
  const Alert(this.message, {super.key, this.tone = ChipTone.warn});

  final String message;
  final ChipTone tone;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (tone) {
      ChipTone.ok => (IbhColors.okBg, IbhColors.okFg),
      ChipTone.bad => (IbhColors.badBg, IbhColors.badFg),
      ChipTone.info => (IbhColors.infoBg, IbhColors.infoFg),
      _ => (IbhColors.warnBg, IbhColors.warnFg),
    };
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(IbhSpace.s12),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(IbhRadius.control)),
      child: Text(message, style: TextStyle(color: fg, fontSize: 14)),
    );
  }
}

/// Shows a failed load with a retry button.
class ErrorRetry extends StatelessWidget {
  const ErrorRetry(this.error, this.onRetry, {super.key});

  final Object error;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final e = ApiError.from(error);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(IbhSpace.s24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(e.friendlyMessage, textAlign: TextAlign.center),
          if (e.requestId != null)
            Text('Ref ${e.requestId}', style: IbhText.mono.copyWith(fontSize: 11)),
          const SizedBox(height: IbhSpace.s16),
          OutlinedButton(onPressed: onRetry, child: const Text('Try again')),
        ]),
      ),
    );
  }
}

void showError(BuildContext context, Object error) {
  final e = ApiError.from(error);
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(e.friendlyMessage)));
}

class WrongRoleScreen extends ConsumerWidget {
  const WrongRoleScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(IbhSpace.s24),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              const Text('This app is for supervisors and contractors.', style: IbhText.h3),
              const SizedBox(height: IbhSpace.s12),
              const Text('Clients, suppliers and the operations team use the iBackHome website.',
                  textAlign: TextAlign.center),
              const SizedBox(height: IbhSpace.s24),
              OutlinedButton(
                  onPressed: () => ref.read(authProvider.notifier).signOut(),
                  child: const Text('Sign out')),
            ]),
          ),
        ),
      );
}

class ConsentScreen extends ConsumerStatefulWidget {
  const ConsentScreen({super.key});

  @override
  ConsumerState<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends ConsumerState<ConsentScreen> {
  bool _busy = false;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(IbhSpace.s24),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Spacer(),
              const Text('Before you start', style: IbhText.h2),
              const SizedBox(height: IbhSpace.s12),
              const Text(
                  'iBackHome records your photos, your location at the shutter and your phone clock to prove what '
                  'happened on site. By continuing you agree to the Terms of Use and the Privacy Policy '
                  '(Nigeria Data Protection Act 2023).'),
              const Spacer(),
              FilledButton(
                onPressed: _busy
                    ? null
                    : () async {
                        setState(() => _busy = true);
                        try {
                          await ref.read(authProvider.notifier).agreeToTerms();
                        } catch (e) {
                          if (context.mounted) showError(context, e);
                        } finally {
                          if (mounted) setState(() => _busy = false);
                        }
                      },
                child: const Text('I agree'),
              ),
              const SizedBox(height: IbhSpace.s8),
              TextButton(
                  onPressed: () => ref.read(authProvider.notifier).signOut(),
                  child: const Text('Sign out')),
            ]),
          ),
        ),
      );
}

/// The three checks shown wherever evidence appears (inside the site, device-signed, not reused).
class ThreeChecksView extends StatelessWidget {
  const ThreeChecksView(this.checks, {super.key});

  final ThreeChecks checks;

  @override
  Widget build(BuildContext context) {
    Widget row(String label, CheckState s) {
      final (icon, color, word) = switch (s) {
        CheckState.pass => (Icons.check_circle, IbhColors.okFg, 'passed'),
        CheckState.fail => (Icons.cancel, IbhColors.badFg, 'failed'),
        CheckState.flagged => (Icons.flag, IbhColors.warnFg, 'sent to ops'),
        CheckState.pending => (Icons.schedule, IbhColors.muted, 'not checked yet'),
      };
      return Padding(
        padding: const EdgeInsets.only(top: 2),
        child: Row(children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 6),
          Expanded(child: Text('$label: $word', style: const TextStyle(fontSize: 13))),
        ]),
      );
    }

    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      row('Inside the site', checks.geofence),
      row('Signed on the device', checks.signed),
      row('Not a reused photo', checks.notReused),
    ]);
  }
}

/// Signing out keeps the queued captures on the phone, but they cannot upload until the same
/// person signs in again. Warn first when some are still waiting (AND-SUPERVISOR-003).
Future<void> confirmSignOut(BuildContext context, WidgetRef ref) async {
  final unsent = await ref.read(servicesProvider).db.unsentCount();
  if (!context.mounted) return;
  final go = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Sign out?'),
      content: Text(unsent == 0
          ? 'You will need a new code to sign in again.'
          : '$unsent capture${unsent == 1 ? ' is' : 's are'} still waiting to upload. They stay safe on this '
              'phone and upload after you sign in again, but they must still reach the server within 72 hours of '
              'being taken.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Stay signed in')),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Sign out')),
      ],
    ),
  );
  if (go == true) await ref.read(authProvider.notifier).signOut();
}
