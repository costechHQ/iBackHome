import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/config.dart';
import '../core/mock_data.dart';
import '../core/money.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/forms.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'arrival_screen.dart';
import 'capture_target.dart';
import 'permissions_screen.dart';
import 'widgets.dart';

final _deliveriesProvider = FutureProvider.autoDispose<List<Map<String, Object?>>>((ref) async {
  final all = await sampleOrders();
  return all.where((o) => o['status'] == 'approved').toList();
});

/// AND-SUPERVISOR-009: orders waiting for a delivery to be confirmed on site.
///
/// SAMPLE DATA: there is no route that lists orders yet (MX-05), so the orders come from
/// `core/mock_data.dart` in debug builds and the list is empty otherwise. Confirming a sample order
/// calls nothing on the server. `POST /orders/{id}/delivery` exists and is used for a real order.
class DeliveriesScreen extends ConsumerWidget {
  const DeliveriesScreen({super.key, required this.projectId, this.projectTitle});
  final String projectId;
  final String? projectTitle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orders = ref.watch(_deliveriesProvider);
    return Scaffold(
      appBar: IbhAppBar(title: 'Deliveries', subtitle: projectTitle),
      body: orders.when(
        loading: () => const SkeletonList(rows: 2),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(_deliveriesProvider)),
        data: (items) => items.isEmpty
            ? const EmptyState(
                icon: Icons.local_shipping_outlined,
                title: 'No deliveries to confirm',
                message: 'When an order is approved and the truck arrives, it shows here for you to count.',
              )
            : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                if (Config.mocks)
                  const Padding(
                    padding: EdgeInsets.only(bottom: IbhSpace.s12),
                    child: Alert('Sample order. The orders list route does not exist yet, so this is not a real delivery.', tone: ChipTone.info),
                  ),
                IbhGroup(children: [
                  for (final o in items)
                    IbhRow(
                      title: '${o['title']}',
                      subtitle: '${o['display_ref']} · ${o['supplier']}',
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => DeliveryScreen(order: {...o, 'project_id': projectId}, projectTitle: projectTitle))),
                    ),
                ]),
              ]),
      ),
    );
  }
}

String _qty(Map<String, Object?> line) => '${line['quantity']} ${line['unit']}${line['quantity'] == '1' ? '' : 's'}';

List<Map<String, Object?>> _lines(Map<String, Object?> order) => (order['items'] as List).cast<Map<String, Object?>>();

/// "Delivery": what should arrive, then "Start counting".
class DeliveryScreen extends StatelessWidget {
  const DeliveryScreen({super.key, required this.order, this.projectTitle});
  final Map<String, Object?> order;
  final String? projectTitle;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Delivery', subtitle: 'Order ${order['display_ref']}${projectTitle == null ? '' : ' · $projectTitle'}'),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          IbhCard(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${order['supplier']}', style: IbhText.h3.copyWith(fontSize: 18)),
              Text('For ${order['milestone']}', style: IbhText.body),
            ]),
          ),
          const IbhSectionLabel('WHAT SHOULD ARRIVE'),
          IbhGroup(children: [
            for (final l in _lines(order))
              IbhRow(
                title: '${l['item']}',
                trailing: Text(_qty(l), style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
              ),
          ]),
          const SizedBox(height: IbhSpace.s12),
          Text('Count everything yourself, on site, before the truck leaves. The supplier is paid from your count.', style: IbhText.small.copyWith(color: IbhColors.muted)),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CountDeliveryScreen(order: order))),
            child: const Text('Start counting'),
          ),
        ]),
      );
}

/// "Count delivery": a count and one photo for each line.
class CountDeliveryScreen extends ConsumerStatefulWidget {
  const CountDeliveryScreen({super.key, required this.order});
  final Map<String, Object?> order;

  @override
  ConsumerState<CountDeliveryScreen> createState() => _CountDeliveryScreenState();
}

class _CountDeliveryScreenState extends ConsumerState<CountDeliveryScreen> {
  late final Services _s = ref.read(servicesProvider);
  late final List<Map<String, Object?>> _items = _lines(widget.order);
  late final Map<String, int> _counts = {for (final l in _items) '${l['item']}': int.tryParse('${l['quantity']}') ?? 0};
  List<QueuedCapture> _photos = const [];
  bool _busy = false;

  String get _ref => 'delivery:${widget.order['id']}';

  @override
  void initState() {
    super.initState();
    _s.sync.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    _s.sync.removeListener(_load);
    super.dispose();
  }

  /// The project the delivery photos belong to (a sample order is given the project it was opened from).
  String get _project => '${widget.order['project_id']}';

  Future<void> _load() async {
    final all = await _s.db.all(projectId: _project);
    if (mounted) setState(() => _photos = all.where((c) => c.contextRef == _ref && c.status != CaptureStatus.draft).toList());
  }

  QueuedCapture? _photoFor(String item) {
    for (final p in _photos) {
      if (p.checklistItem == item) return p;
    }
    return null;
  }

  int get _missing => _items.where((l) => _photoFor('${l['item']}') == null).length;

  Future<void> _photo(String item) async {
    if (!await ensureCaptureReady(context, ref) || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => ArrivalScreen(
        target: CaptureTarget(
          projectId: _project,
          title: item,
          subtitle: 'Order ${widget.order['display_ref']}',
          contextRef: _ref,
          fixedItem: item,
        ),
      ),
    ));
    await _load();
  }

  Future<void> _confirm() async {
    setState(() => _busy = true);
    try {
      if (widget.order['_mock'] != true) {
        // A real order: the server needs the evidence ids, so every photo must be accepted first.
        final ids = [for (final l in _items) _photoFor('${l['item']}')?.evidenceId];
        if (ids.any((i) => i == null)) {
          if (mounted) showError(context, 'Wait until your photos are accepted (see the Sync tab), then confirm.');
          return;
        }
        await _s.api.post<Map<String, dynamic>>('/orders/${widget.order['id']}/delivery', body: {
          'quantities': {for (final e in _counts.entries) e.key: '${e.value}'},
          'evidence_ids': ids,
        });
      }
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(MaterialPageRoute<void>(
          builder: (_) => DeliveryConfirmedScreen(order: widget.order, photos: _photos.length, sample: widget.order['_mock'] == true)));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Count delivery', subtitle: '${widget.order['display_ref']} · ${_items.length} items'),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          IbhGroup(children: [
            for (final l in _items) _line(l),
          ]),
          const SizedBox(height: IbhSpace.s12),
          Container(
            padding: const EdgeInsets.all(IbhSpace.s16),
            decoration: BoxDecoration(color: IbhColors.neutralBg, borderRadius: BorderRadius.circular(IbhRadius.card)),
            child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.info_outline, size: 20),
              SizedBox(width: IbhSpace.s12),
              Expanded(child: Text('Each line needs one photo showing the count.', style: IbhText.body)),
            ]),
          ),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: _busy || _missing > 0 ? null : _confirm, child: const Text('Confirm delivery')),
          if (_missing > 0) Text('$_missing photo${_missing == 1 ? '' : 's'} still needed', textAlign: TextAlign.center, style: IbhText.small.copyWith(color: IbhColors.muted)),
        ]),
      );

  Widget _line(Map<String, Object?> l) {
    final item = '${l['item']}';
    final photo = _photoFor(item);
    final ordered = int.tryParse('${l['quantity']}') ?? 0;
    return Padding(
      padding: const EdgeInsets.all(IbhSpace.s16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$item, ${l['unit']}s', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
        const SizedBox(height: IbhSpace.s8),
        Row(children: [
          CountStepper(value: _counts[item]!, label: item, max: 100000, onChanged: (v) => setState(() => _counts[item] = v)),
          const SizedBox(width: IbhSpace.s12),
          Expanded(child: Text('of $ordered ordered', style: IbhText.small)),
          if (photo != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(color: IbhColors.mist, borderRadius: BorderRadius.circular(IbhRadius.tag), border: Border.all(color: IbhColors.line)),
              child: Text(photo.evidenceId == null ? 'Photo saved' : 'EV-${photo.evidenceId!.substring(0, 4).toUpperCase()}', style: IbhText.mono.copyWith(fontSize: 12)),
            )
          else
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size(96, 48)),
              onPressed: () => _photo(item),
              icon: const Icon(Icons.photo_camera_outlined, size: 20),
              label: const Text('Photo'),
            ),
        ]),
      ]),
    );
  }
}

/// "Delivery confirmed": the supplier is paid from the milestone escrow after the photos are accepted.
class DeliveryConfirmedScreen extends StatelessWidget {
  const DeliveryConfirmedScreen({super.key, required this.order, required this.photos, required this.sample});
  final Map<String, Object?> order;
  final int photos;
  final bool sample;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Delivery', subtitle: '${order['display_ref']}', leading: IbhBarLeading.none),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.check, ok: true)),
          const SizedBox(height: IbhSpace.s16),
          Text('Delivery confirmed', style: IbhText.h2.copyWith(fontSize: 26)),
          const SizedBox(height: IbhSpace.s12),
          Text('Your $photos photo${photos == 1 ? ' is' : 's are'} uploading.', style: IbhText.bodyLg),
          const SizedBox(height: IbhSpace.s16),
          IbhCard(
            child: Column(children: [
              _kv('Confirmed', watDayTime(DateTime.now())),
              _kv('Photos', '$photos'),
              _kv('Supplier payment', 'After your photos are accepted'),
            ]),
          ),
          const SizedBox(height: IbhSpace.s12),
          Text(
            '${order['supplier']} is paid ${formatMoney(order['total_minor'] as int, currency: '${order['currency']}')} from the ${order['milestone']} escrow, held by a licensed escrow partner, never by iBackHome.',
            style: IbhText.small.copyWith(color: IbhColors.muted),
          ),
          if (sample) ...[
            const SizedBox(height: IbhSpace.s12),
            const Alert('Sample order: nothing was sent to the server.', tone: ChipTone.info),
          ],
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst || r.settings.name == '/'), child: const Text('Done')),
        ]),
      );

  static Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(k, style: IbhText.body.copyWith(color: IbhColors.muted)),
          const SizedBox(width: IbhSpace.s12),
          Expanded(child: Text(v, textAlign: TextAlign.right, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink))),
        ]),
      );
}
