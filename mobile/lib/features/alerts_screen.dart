import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'projects_tab.dart' show SavedNote;
import 'widgets.dart';

/// The signed-in user's own notifications (`GET /me/notifications`, MX-11): the newest 50, and how many
/// are unread in all (for the tab badge).
class AlertsFeed {
  const AlertsFeed(this.items, this.unread);
  final List<Map<String, dynamic>> items;
  final int unread;
}

final alertsProvider = FutureProvider.autoDispose<AlertsFeed>((ref) async {
  final page = await ref.read(servicesProvider).cachedGet<Map<String, dynamic>>('/me/notifications', query: {'limit': 50});
  return AlertsFeed((page['items'] as List).cast<Map<String, dynamic>>(), (page['unread_count'] as num?)?.toInt() ?? 0);
});

/// AND-CONTRACTOR-005, the Alerts tab: verified, sent back, released and dispute updates, as the
/// server sent them. Opening an unread one marks it read. With no signal the last saved list shows.
class AlertsTab extends ConsumerWidget {
  const AlertsTab({super.key});

  /// Marks one read on the server, then reads the list again. Without signal it stays unread and is
  /// marked next time; that is not worth an error.
  static Future<void> _open(WidgetRef ref, Map<String, dynamic> a) async {
    if (a['read_at'] != null) return;
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>('/me/notifications/${a['id']}/read', idempotencyKey: 'read-${a['id']}');
      ref.invalidate(alertsProvider);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerts = ref.watch(alertsProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.refresh(alertsProvider.future),
      child: alerts.when(
        loading: () => const SkeletonList(rows: 3),
        error: (e, _) => ListView(children: [SizedBox(height: 320, child: ErrorRetry(e, () => ref.invalidate(alertsProvider)))]),
        data: (feed) => feed.items.isEmpty
            ? ListView(children: const [
                SizedBox(
                  height: 420,
                  child: EmptyState(
                    icon: Icons.notifications_none,
                    title: 'No alerts yet',
                    message: 'When a milestone is verified, sent back or paid, it shows here. You also get it by WhatsApp or SMS.',
                  ),
                ),
              ])
            : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                const SavedNote(),
                IbhGroup(children: [for (final a in feed.items) _AlertRow(a, onTap: () => _open(ref, a))]),
              ]),
      ),
    );
  }
}

class _AlertRow extends StatelessWidget {
  const _AlertRow(this.a, {required this.onTap});
  final Map<String, dynamic> a;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final unread = a['read_at'] == null;
    final at = DateTime.tryParse('${a['created_at']}');
    return InkWell(
      onTap: unread ? onTap : null,
      child: Container(
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
              Text('${a['text']}', style: IbhText.body),
              if (at != null) ...[
                const SizedBox(height: 4),
                Text(watDayTime(at), style: IbhText.small.copyWith(color: IbhColors.muted)),
              ],
            ]),
          ),
        ]),
      ),
    );
  }
}
