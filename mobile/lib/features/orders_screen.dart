import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/money.dart';
import '../core/orders.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'home_screen.dart';
import 'projects_tab.dart' show SavedNote;
import 'widgets.dart';

/// The signed-in contractor's orders across all their projects, newest first (`GET /projects/{id}/orders`,
/// one call per project). Each carries its project's title so a contractor on several sites can tell them apart.
final ordersProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final projects = await ref.watch(projectsProvider.future);
  final s = ref.read(servicesProvider);
  final pages = await Future.wait([
    for (final p in projects) s.cachedGet<Map<String, dynamic>>('/projects/${p['id']}/orders', query: {'limit': 50}),
  ]);
  final all = <Map<String, dynamic>>[
    for (var i = 0; i < projects.length; i++)
      for (final o in (pages[i]['items'] as List).cast<Map<String, dynamic>>()) {...o, 'project_title': projects[i]['title']},
  ];
  all.sort((a, b) => '${b['created_at']}'.compareTo('${a['created_at']}'));
  return all;
});

({String label, ChipTone tone}) orderChip(String status) => switch (status) {
      'requested' => (label: 'Waiting for the client', tone: ChipTone.warn),
      'approved' => (label: 'Approved', tone: ChipTone.info),
      'delivered' => (label: 'Delivered', tone: ChipTone.neutral),
      'paid' => (label: 'Paid', tone: ChipTone.ok),
      'cancelled' => (label: 'Cancelled', tone: ChipTone.neutral),
      _ => (label: status, tone: ChipTone.neutral),
    };

/// AND-CONTRACTOR-004, the Orders tab: material orders and where each stands, as the server has them.
/// Requesting materials is not in the app yet (it needs the supplier list), so that button points to the web.
class OrdersTab extends ConsumerWidget {
  const OrdersTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orders = ref.watch(ordersProvider);
    return orders.when(
      loading: () => const SkeletonList(rows: 3),
      error: (e, _) => ErrorRetry(e, () => ref.invalidate(ordersProvider)),
      data: (items) => Column(children: [
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(projectsProvider);
              await ref.refresh(ordersProvider.future); // ignore: unused_result
            },
            child: items.isEmpty
                ? ListView(children: const [
                    SizedBox(
                      height: 420,
                      child: EmptyState(
                        icon: Icons.inventory_2_outlined,
                        title: 'No orders yet',
                        message: 'Request materials on the iBackHome website. Each order, its delivery and its payment show here.',
                      ),
                    ),
                  ])
                : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                    const SavedNote(),
                    for (final o in items)
                      Padding(
                        padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                        child: _OrderCard(o),
                      ),
                    const SizedBox(height: IbhSpace.s4),
                    Text('Supplier payments come out of the milestone\'s escrow, held by a licensed escrow partner, never by iBackHome.',
                        style: IbhText.small.copyWith(color: IbhColors.muted)),
                  ]),
          ),
        ),
        BottomActionBar(children: [
          FilledButton(
            onPressed: () => ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(const SnackBar(content: Text('Requesting materials is on the web portal for now.'))),
            child: const Text('Request materials'),
          ),
        ]),
      ]),
    );
  }
}

/// "sent Thu 7 Jan", or "delivered Fri 18 Dec" once the supervisor has counted it.
String orderWhen(Map<String, dynamic> o) {
  final delivered = DateTime.tryParse('${(o['delivery'] as Map?)?['confirmed_at']}');
  if (delivered != null) return 'delivered ${watDay(delivered)}';
  final sent = DateTime.tryParse('${o['created_at']}');
  return sent == null ? '' : 'sent ${watDay(sent)}';
}

class _OrderCard extends StatelessWidget {
  const _OrderCard(this.o);
  final Map<String, dynamic> o;

  @override
  Widget build(BuildContext context) {
    final chip = orderChip('${o['status']}');
    final when = orderWhen(o);
    return IbhCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Text(supplierName(o), style: IbhText.h3.copyWith(fontSize: 18))),
          const SizedBox(width: IbhSpace.s8),
          StatusChip(chip.label, tone: chip.tone),
        ]),
        const SizedBox(height: IbhSpace.s4),
        Text(itemsSummary(o), style: IbhText.body.copyWith(color: IbhColors.ink)),
        Text('${orderRef(o['id'])} · ${o['project_title']}${when.isEmpty ? '' : ' · $when'}', style: IbhText.body),
        const SizedBox(height: IbhSpace.s8),
        Text(formatMoney(o['total_minor'] as int, currency: '${o['currency']}'), style: IbhText.h3.copyWith(fontSize: 18)),
      ]),
    );
  }
}
