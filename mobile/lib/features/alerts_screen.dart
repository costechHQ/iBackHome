import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/config.dart';
import '../core/mock_data.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'widgets.dart';

final alertsProvider = FutureProvider.autoDispose<List<Map<String, Object?>>>((ref) => sampleAlerts());

/// AND-CONTRACTOR-005, the Alerts tab: verified, sent back, released and dispute updates.
///
/// SAMPLE DATA: the in-app feed route does not exist yet (MX-11), so alerts come from
/// `core/mock_data.dart` in debug builds and the list is empty otherwise. Messages still reach the
/// contractor by WhatsApp, SMS and email.
class AlertsTab extends ConsumerWidget {
  const AlertsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerts = ref.watch(alertsProvider);
    return alerts.when(
      loading: () => const SkeletonList(rows: 3),
      error: (e, _) => ErrorRetry(e, () => ref.invalidate(alertsProvider)),
      data: (items) => items.isEmpty
          ? const EmptyState(
              icon: Icons.notifications_none,
              title: 'No alerts yet',
              message: 'When a milestone is verified, sent back or paid, it shows here. You also get it by WhatsApp or SMS.',
            )
          : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
              if (Config.mocks)
                const Padding(
                  padding: EdgeInsets.only(bottom: IbhSpace.s12),
                  child: Alert('Sample alerts. The alerts feed does not exist yet, so these are not your real alerts.', tone: ChipTone.info),
                ),
              IbhGroup(children: [for (final a in items) _AlertRow(a)]),
            ]),
    );
  }
}

class _AlertRow extends StatelessWidget {
  const _AlertRow(this.a);
  final Map<String, Object?> a;

  @override
  Widget build(BuildContext context) {
    final unread = a['unread'] == true;
    final at = DateTime.tryParse('${a['sent_at']}');
    return Container(
      color: unread ? IbhColors.white : IbhColors.mist,
      padding: const EdgeInsets.all(IbhSpace.s16),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
          width: 16,
          child: unread
              ? const Padding(
                  padding: EdgeInsets.only(top: 6),
                  child: CircleAvatar(radius: 4, backgroundColor: IbhColors.accent),
                )
              : null,
        ),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${a['title']}${unread ? ' (unread)' : ''}', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
            const SizedBox(height: 2),
            Text('${a['body']}', style: IbhText.body),
            if (at != null) ...[
              const SizedBox(height: 4),
              Text(watDayTime(at), style: IbhText.small.copyWith(color: IbhColors.muted)),
            ],
          ]),
        ),
      ]),
    );
  }
}
