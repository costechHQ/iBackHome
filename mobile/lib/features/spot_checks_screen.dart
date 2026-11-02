import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/forms.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/sheets.dart';
import '../ui/states.dart';
import 'arrival_screen.dart';
import 'capture_target.dart';
import 'permissions_screen.dart';
import 'widgets.dart';

final spotChecksProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final list = await ref.read(servicesProvider).api.get<List<dynamic>>('/supervisors/me/spot-checks');
  return list.cast<Map<String, dynamic>>();
});

({String label, ChipTone tone}) _spotChip(Map<String, dynamic> s) {
  if (s['completed_at'] != null) return (label: 'Submitted', tone: ChipTone.ok);
  final due = DateTime.parse(s['scheduled_for'] as String);
  final now = DateTime.now().toUtc();
  if (due.isBefore(now)) return (label: 'Due now', tone: ChipTone.warn);
  final sameDay = watDay(due) == watDay(now);
  return sameDay ? (label: 'Today', tone: ChipTone.warn) : (label: 'Scheduled', tone: ChipTone.neutral);
}

/// AND-SUPERVISOR-010, the Spot checks tab: unannounced visits to make, and the ones done.
///
/// Spot checks are unannounced: the contractor is never told, and the client sees the result only
/// after operations close it. The project name and address are not shown (the API does not send them,
/// on purpose).
class SpotChecksScreen extends ConsumerWidget {
  const SpotChecksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final checks = ref.watch(spotChecksProvider);
    Future<void> open(Map<String, dynamic> s) async {
      await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => SpotCheckScreen(spotCheck: s)));
      ref.invalidate(spotChecksProvider);
    }

    return RefreshIndicator(
      onRefresh: () async => ref.refresh(spotChecksProvider.future),
      child: checks.when(
        loading: () => const SkeletonList(rows: 3),
        error: (e, _) => ListView(children: [SizedBox(height: 320, child: ErrorRetry(e, () => ref.invalidate(spotChecksProvider)))]),
        data: (items) {
          if (items.isEmpty) {
            return ListView(children: const [
              SizedBox(
                height: 420,
                child: EmptyState(
                  icon: Icons.event_outlined,
                  title: 'No spot checks',
                  message: 'Unannounced checks appear here when iBackHome assigns one.',
                ),
              ),
            ]);
          }
          final todo = items.where((s) => s['completed_at'] == null).toList();
          final done = items.where((s) => s['completed_at'] != null).toList();
          return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
            Container(
              padding: const EdgeInsets.all(IbhSpace.s16),
              decoration: BoxDecoration(color: IbhColors.neutralBg, borderRadius: BorderRadius.circular(IbhRadius.card)),
              child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.lock_outline, size: 20),
                SizedBox(width: IbhSpace.s12),
                Expanded(
                  child: Text('Don\'t tell the contractor you\'re coming. Spot checks are only visible to you and iBackHome.', style: IbhText.body),
                ),
              ]),
            ),
            if (todo.isNotEmpty) ...[
              const IbhSectionLabel('ASSIGNED'),
              for (final s in todo)
                Padding(
                  padding: const EdgeInsets.only(bottom: IbhSpace.s8),
                  child: IbhCard(
                    emphasis: _spotChip(s).label != 'Scheduled',
                    onTap: () => open(s),
                    child: Row(children: [
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('Site visit', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
                          Text(watDayTime(DateTime.parse(s['scheduled_for'] as String)), style: IbhText.small),
                        ]),
                      ),
                      StatusChip(_spotChip(s).label, tone: _spotChip(s).tone),
                    ]),
                  ),
                ),
            ],
            if (done.isNotEmpty) ...[
              const IbhSectionLabel('DONE'),
              IbhGroup(children: [
                for (final s in done)
                  IbhRow(
                    title: 'Site visit',
                    subtitle: watDayTime(DateTime.parse(s['completed_at'] as String)),
                    trailing: const StatusChip('Submitted', tone: ChipTone.ok),
                    onTap: () => open(s),
                  ),
              ]),
            ],
          ]);
        },
      ),
    );
  }
}

/// One spot check: the short, factual form, then the "findings sent" page.
class SpotCheckScreen extends ConsumerStatefulWidget {
  const SpotCheckScreen({super.key, required this.spotCheck});
  final Map<String, dynamic> spotCheck;

  @override
  ConsumerState<SpotCheckScreen> createState() => _SpotCheckScreenState();
}

class _SpotCheckScreenState extends ConsumerState<SpotCheckScreen> {
  final _doesntMatch = TextEditingController();
  List<QueuedCapture> _captures = const [];
  String? _matches; // yes | partly | no
  String? _materials; // yes | no | none
  int _workers = 0;
  bool _busy = false;
  DateTime? _sentAt; // set once submitted in this visit to the screen

  String get _ref => 'spot_check:${widget.spotCheck['id']}';
  bool get _done => widget.spotCheck['completed_at'] != null || _sentAt != null;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _doesntMatch.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final all = await ref.read(servicesProvider).db.all(projectId: widget.spotCheck['project_id'] as String);
    if (mounted) setState(() => _captures = all.where((c) => c.contextRef == _ref && c.status != CaptureStatus.draft).toList());
  }

  Future<void> _capture() async {
    if (!await ensureCaptureReady(context, ref) || !mounted) return;
    await Navigator.of(context).push(MaterialPageRoute<void>(
      builder: (_) => ArrivalScreen(
        target: CaptureTarget(
          projectId: widget.spotCheck['project_id'] as String,
          title: 'Spot check',
          contextRef: _ref,
          // The visiting supervisor is not a member of the project, so the site boundary is not
          // available to the app; the server does the boundary check.
        ),
      ),
    ));
    await _load();
  }

  bool get _needsText => _matches == 'partly' || _matches == 'no';
  bool get _canSubmit => _matches != null && _materials != null && _captures.isNotEmpty && (!_needsText || _doesntMatch.text.trim().length >= 10);

  /// The API has one text field, so the answers go in as one plain-language sentence each.
  String get _findings => composeSpotFindings(
        matches: _matches ?? 'no',
        doesntMatch: _doesntMatch.text,
        materials: _materials ?? 'none',
        workers: _workers,
        captures: _captures.length,
      );

  Future<void> _submit() async {
    final go = await confirmSheet(
      context,
      title: 'Submit spot check findings?',
      message: "They go to iBackHome only. You can't edit them afterwards.",
      confirmLabel: 'Submit findings',
      cancelLabel: 'Keep editing',
    );
    if (!go || !mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/spot-checks/${widget.spotCheck['id']}/complete',
        body: {'findings': _findings},
        idempotencyKey: 'spot-${widget.spotCheck['id']}',
      );
      if (mounted) setState(() => _sentAt = DateTime.now());
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final when = watDayTime(DateTime.parse(widget.spotCheck['scheduled_for'] as String));
    return Scaffold(
      appBar: IbhAppBar(title: 'Spot check', subtitle: 'Site visit · $when'),
      body: _done ? _sent() : _form(),
      bottomNavigationBar: _done
          ? BottomActionBar(children: [FilledButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Back to spot checks'))])
          : BottomActionBar(children: [
              FilledButton(onPressed: _busy || !_canSubmit ? null : _submit, child: _busy ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: IbhColors.white)) : const Text('Submit findings')),
            ]),
    );
  }

  Widget _form() => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const Text('Does the work match the latest claim?', style: _label),
        const SizedBox(height: IbhSpace.s8),
        ChoiceRow<String>(options: const {'yes': 'Yes', 'partly': 'Partly', 'no': 'No'}, value: _matches, onChanged: (v) => setState(() => _matches = v)),
        if (_needsText) ...[
          const SizedBox(height: IbhSpace.s16),
          const Text('What doesn\'t match', style: _label),
          const SizedBox(height: IbhSpace.s8),
          TextField(controller: _doesntMatch, maxLines: 4, textCapitalization: TextCapitalization.sentences, onChanged: (_) => setState(() {})),
          const SizedBox(height: 4),
          Text('At least 10 characters', style: IbhText.small.copyWith(color: IbhColors.muted)),
        ],
        const SizedBox(height: IbhSpace.s16),
        const Text('Materials on site match approved orders?', style: _label),
        const SizedBox(height: IbhSpace.s8),
        ChoiceRow<String>(options: const {'yes': 'Yes', 'no': 'No', 'none': 'No orders'}, value: _materials, onChanged: (v) => setState(() => _materials = v)),
        const SizedBox(height: IbhSpace.s16),
        const Text('Workers on site', style: _label),
        const SizedBox(height: IbhSpace.s8),
        Align(alignment: Alignment.centerLeft, child: CountStepper(value: _workers, max: 500, label: 'workers', onChanged: (v) => setState(() => _workers = v))),
        const SizedBox(height: IbhSpace.s16),
        IbhCard(
          child: Row(children: [
            Expanded(
              child: Text.rich(TextSpan(style: IbhText.body, children: [
                TextSpan(text: '${_captures.length} capture${_captures.length == 1 ? '' : 's'}', style: const TextStyle(fontWeight: FontWeight.w700, color: IbhColors.ink)),
                if (_captures.isEmpty) const TextSpan(text: ' · take at least one'),
              ])),
            ),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size(96, 48)),
              onPressed: _capture,
              icon: const Icon(Icons.photo_camera_outlined, size: 20),
              label: const Text('Add'),
            ),
          ]),
        ),
        const SizedBox(height: IbhSpace.s12),
        const Alert('Unannounced visit. Do not tell the contractor. The client sees the result only after operations close the check.', tone: ChipTone.info),
      ]);

  Widget _sent() {
    final at = _sentAt ?? DateTime.tryParse('${widget.spotCheck['completed_at']}');
    final waiting = _captures.where((c) => CaptureStatus.open.contains(c.status)).length;
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.check, ok: true)),
      const SizedBox(height: IbhSpace.s16),
      Text('Findings sent to iBackHome', style: IbhText.h2.copyWith(fontSize: 26)),
      const SizedBox(height: IbhSpace.s12),
      const Text('Our team compares them with the contractor\'s claim. The client sees the spot check only after we close it.', style: IbhText.bodyLg),
      const SizedBox(height: IbhSpace.s16),
      IbhCard(
        child: Column(children: [
          if (at != null) _kv('Submitted', watDayTime(at)),
          if (_sentAt != null) _kv('Matches the claim', switch (_matches) { 'yes' => 'Yes', 'partly' => 'Partly', _ => 'No' }),
          _kv('Captures', '${_captures.length}${waiting > 0 ? ' · uploading' : ''}'),
        ]),
      ),
      if (_sentAt == null && widget.spotCheck['findings'] != null) ...[
        const SizedBox(height: IbhSpace.s12),
        IbhCard(child: Text('${widget.spotCheck['findings']}', style: IbhText.body)),
      ],
    ]);
  }

  static Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: IbhText.body.copyWith(color: IbhColors.muted)),
          Text(v, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
        ]),
      );
}

/// The spot-check answers as the single `findings` text the API takes (10 to 5000 characters).
/// [matches] is yes | partly | no; [materials] is yes | no | none.
String composeSpotFindings({required String matches, required String doesntMatch, required String materials, required int workers, required int captures}) {
  final match = switch (matches) { 'yes' => 'Yes', 'partly' => 'Partly', _ => 'No' };
  final mats = switch (materials) { 'yes' => 'Yes', 'no' => 'No', _ => 'No orders' };
  return [
    'The work matches the latest claim: $match.',
    if (matches != 'yes' && doesntMatch.trim().isNotEmpty) "What doesn't match: ${doesntMatch.trim()}",
    'Materials on site match approved orders: $mats.',
    'Workers on site: $workers.',
    'Captures: $captures.',
  ].join(' ');
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);
