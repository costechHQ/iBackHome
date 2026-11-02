import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/money.dart';
import '../core/orders.dart';
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
import 'projects_tab.dart' show SavedNote;
import 'widgets.dart';

/// The project's approved orders, waiting for the supervisor to count them (`GET /projects/{id}/orders`).
final _deliveriesProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>((ref, projectId) async {
  final page = await ref.read(servicesProvider).cachedGet<Map<String, dynamic>>('/projects/$projectId/orders', query: {'limit': 50});
  return (page['items'] as List).cast<Map<String, dynamic>>().where((o) => o['status'] == 'approved').toList();
});

/// AND-SUPERVISOR-009: orders waiting for a delivery to be confirmed on site.
class DeliveriesScreen extends ConsumerWidget {
  const DeliveriesScreen({super.key, required this.projectId, this.projectTitle});
  final String projectId;
  final String? projectTitle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orders = ref.watch(_deliveriesProvider(projectId));
    return Scaffold(
      appBar: IbhAppBar(title: 'Deliveries', subtitle: projectTitle),
      body: RefreshIndicator(
        onRefresh: () async => ref.refresh(_deliveriesProvider(projectId).future),
        child: orders.when(
          loading: () => const SkeletonList(rows: 2),
          error: (e, _) => ListView(children: [SizedBox(height: 320, child: ErrorRetry(e, () => ref.invalidate(_deliveriesProvider(projectId))))]),
          data: (items) => items.isEmpty
              ? ListView(children: const [
                  SizedBox(
                    height: 420,
                    child: EmptyState(
                      icon: Icons.local_shipping_outlined,
                      title: 'No deliveries to confirm',
                      message: 'When an order is approved and the truck arrives, it shows here for you to count.',
                    ),
                  ),
                ])
              : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                  const SavedNote(),
                  IbhGroup(children: [
                    for (final o in items)
                      IbhRow(
                        title: supplierName(o),
                        subtitle: '${orderRef(o['id'])} · ${itemsSummary(o)}',
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () async {
                          await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => DeliveryScreen(order: o, projectTitle: projectTitle)));
                          ref.invalidate(_deliveriesProvider(projectId));
                        },
                      ),
                  ]),
                ]),
        ),
      ),
    );
  }
}

/// "Delivery": what should arrive, then "Start counting".
class DeliveryScreen extends StatelessWidget {
  const DeliveryScreen({super.key, required this.order, this.projectTitle});
  final Map<String, dynamic> order;
  final String? projectTitle;

  @override
  Widget build(BuildContext context) {
    final approved = DateTime.tryParse('${order['approved_at']}');
    return Scaffold(
      appBar: IbhAppBar(title: 'Delivery', subtitle: 'Order ${orderRef(order['id'])}${projectTitle == null ? '' : ' · $projectTitle'}'),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        IbhCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(supplierName(order), style: IbhText.h3.copyWith(fontSize: 18)),
            if (approved != null) Text('Approved ${watDay(approved)}', style: IbhText.body),
          ]),
        ),
        const IbhSectionLabel('WHAT SHOULD ARRIVE'),
        IbhGroup(children: [
          for (final l in orderLines(order))
            IbhRow(
              title: '${l['item']}',
              trailing: Text(quantityLabel(l), style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
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
}

/// "Count delivery": a count and one photo for each line. Counts are exact (whole thousandths): the server
/// accepts only the full ordered quantity for now.
class CountDeliveryScreen extends ConsumerStatefulWidget {
  const CountDeliveryScreen({super.key, required this.order});
  final Map<String, dynamic> order;

  @override
  ConsumerState<CountDeliveryScreen> createState() => _CountDeliveryScreenState();
}

class _CountDeliveryScreenState extends ConsumerState<CountDeliveryScreen> {
  late final Services _s = ref.read(servicesProvider);
  late final List<Map<String, dynamic>> _items = orderLines(widget.order);

  /// Item -> the count in thousandths, or null while a typed number is not a valid decimal.
  late final Map<String, int?> _counts = {for (final l in _items) '${l['item']}': parseMilli('${l['quantity']}') ?? 0};
  List<QueuedCapture> _photos = const [];
  bool _busy = false;

  String get _ref => 'delivery:${widget.order['id']}';
  String get _project => '${widget.order['project_id']}';

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
  bool get _countsValid => _counts.values.every((c) => c != null);

  Future<void> _photo(String item) async {
    if (!await ensureCaptureReady(context, ref) || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => ArrivalScreen(
        target: CaptureTarget(
          projectId: _project,
          title: item,
          subtitle: 'Order ${orderRef(widget.order['id'])}',
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
      // The server needs the evidence ids, so every photo must be accepted first.
      final ids = [for (final l in _items) _photoFor('${l['item']}')?.evidenceId];
      if (ids.any((i) => i == null)) {
        if (mounted) showError(context, 'Wait until your photos are accepted (see the Sync tab), then confirm.');
        return;
      }
      await _s.api.post<Map<String, dynamic>>(
        '/orders/${widget.order['id']}/delivery',
        // One idempotency key per order: a retry after a lost answer replays instead of counting twice.
        idempotencyKey: 'delivery-${widget.order['id']}',
        body: {
          'quantities': [
            for (final l in _items) {'item': '${l['item']}', 'quantity': milliText(_counts['${l['item']}']!)},
          ],
          'evidence_ids': ids,
        },
      );
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(MaterialPageRoute<void>(builder: (_) => DeliveryConfirmedScreen(order: widget.order, photos: _photos.length)));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Count delivery', subtitle: '${orderRef(widget.order['id'])} · ${_items.length} items'),
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
              Expanded(child: Text('Each line needs one photo showing the count. The count must match the order.', style: IbhText.body)),
            ]),
          ),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: _busy || _missing > 0 || !_countsValid ? null : _confirm, child: const Text('Confirm delivery')),
          if (_missing > 0) Text('$_missing photo${_missing == 1 ? '' : 's'} still needed', textAlign: TextAlign.center, style: IbhText.small.copyWith(color: IbhColors.muted)),
        ]),
      );

  Widget _line(Map<String, dynamic> l) {
    final item = '${l['item']}';
    final photo = _photoFor(item);
    final ordered = parseMilli('${l['quantity']}') ?? 0;
    return Padding(
      padding: const EdgeInsets.all(IbhSpace.s16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$item, ${l['unit']}s', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
        const SizedBox(height: IbhSpace.s8),
        Row(children: [
          if (isWhole(ordered))
            CountStepper(value: (_counts[item] ?? 0) ~/ 1000, label: item, max: 100000, onChanged: (v) => setState(() => _counts[item] = v * 1000))
          else
            SizedBox(width: 148, child: DecimalCountField(label: item, initial: milliText(_counts[item] ?? 0), onChanged: (v) => setState(() => _counts[item] = v))),
          const SizedBox(width: IbhSpace.s12),
          Expanded(child: Text('of ${milliText(ordered)} ordered', style: IbhText.small)),
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

/// A count with decimals ("2.5" tonnes), for a line whose ordered quantity is not a whole number. Reports the
/// count in thousandths, or null while what is typed is not a plain decimal of at most three places.
class DecimalCountField extends StatelessWidget {
  const DecimalCountField({super.key, required this.label, required this.initial, required this.onChanged});
  final String label;
  final String initial;
  final ValueChanged<int?> onChanged;

  @override
  Widget build(BuildContext context) => TextFormField(
        initialValue: initial,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
        decoration: InputDecoration(labelText: 'Count of $label', helperText: 'Up to 3 decimals'),
        validator: (v) => parseMilli(v ?? '') == null ? 'Enter a number like 2.5' : null,
        autovalidateMode: AutovalidateMode.always,
        onChanged: (v) => onChanged(parseMilli(v)),
      );
}

/// "Delivery confirmed": the supplier is paid from the milestone escrow after the photos are accepted.
class DeliveryConfirmedScreen extends StatelessWidget {
  const DeliveryConfirmedScreen({super.key, required this.order, required this.photos});
  final Map<String, dynamic> order;
  final int photos;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Delivery', subtitle: orderRef(order['id']), leading: IbhBarLeading.none),
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
            '${supplierName(order)} is paid ${formatMoney(order['total_minor'] as int, currency: '${order['currency']}')} from escrow, held by a licensed escrow partner, never by iBackHome.',
            style: IbhText.small.copyWith(color: IbhColors.muted),
          ),
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
