import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/config.dart';
import '../core/mock_data.dart';
import '../core/money.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'widgets.dart';

final ordersProvider = FutureProvider.autoDispose<List<Map<String, Object?>>>((ref) => sampleOrders());

({String label, ChipTone tone}) orderChip(String status) => switch (status) {
      'requested' => (label: 'Waiting for the client', tone: ChipTone.warn),
      'approved' => (label: 'Approved', tone: ChipTone.info),
      'delivered' => (label: 'Delivered', tone: ChipTone.neutral),
      'paid' => (label: 'Paid', tone: ChipTone.ok),
      'cancelled' => (label: 'Cancelled', tone: ChipTone.neutral),
      _ => (label: status, tone: ChipTone.neutral),
    };

/// AND-CONTRACTOR-004, the Orders tab: material orders and where each stands.
///
/// SAMPLE DATA: there is no route that lists a project's orders yet (MX-05), so the list comes from
/// `core/mock_data.dart` in debug builds and is empty otherwise. Requesting materials is not in the app
/// yet either (it needs the supplier list).
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
          child: items.isEmpty
              ? const EmptyState(
                  icon: Icons.inventory_2_outlined,
                  title: 'Orders are on the web portal for now',
                  message: 'Request materials and follow their delivery and payment on the iBackHome website.',
                )
              : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                  if (Config.mocks)
                    const Padding(
                      padding: EdgeInsets.only(bottom: IbhSpace.s12),
                      child: Alert('Sample orders. The list route does not exist yet, so these are not your real orders.', tone: ChipTone.info),
                    ),
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

class _OrderCard extends StatelessWidget {
  const _OrderCard(this.o);
  final Map<String, Object?> o;

  @override
  Widget build(BuildContext context) {
    final chip = orderChip('${o['status']}');
    final when = DateTime.tryParse('${o['created_at']}');
    return IbhCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Text('${o['title']}', style: IbhText.h3.copyWith(fontSize: 18))),
          const SizedBox(width: IbhSpace.s8),
          StatusChip(chip.label, tone: chip.tone),
        ]),
        const SizedBox(height: IbhSpace.s4),
        Text('${o['display_ref']} · ${o['milestone']}${when == null ? '' : ' · ${watDay(when)}'}', style: IbhText.body),
        const SizedBox(height: IbhSpace.s8),
        Text(formatMoney(o['total_minor'] as int, currency: '${o['currency']}'), style: IbhText.h3.copyWith(fontSize: 18)),
      ]),
    );
  }
}
