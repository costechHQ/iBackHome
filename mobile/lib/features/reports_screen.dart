import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/markdown_lite.dart';
import '../ui/sheets.dart';
import '../ui/states.dart';
import 'widgets.dart';

final reportsProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>((ref, projectId) async {
  final list = await ref.read(servicesProvider).api.get<List<dynamic>>('/projects/$projectId/reports');
  return list.cast<Map<String, dynamic>>()..sort((a, b) => (b['week_start'] as String).compareTo(a['week_start'] as String));
});

({String label, ChipTone tone}) _reportChip(String status) => switch (status) {
      'draft' => (label: 'Needs your review', tone: ChipTone.warn),
      'reviewed' => (label: 'Reviewed', tone: ChipTone.ok),
      _ => (label: 'Sent', tone: ChipTone.ok),
    };

const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/// `4 Jan` from the report's `week_start` (a plain date).
String _weekOf(String iso) {
  final d = DateTime.tryParse(iso);
  return d == null ? iso : '${d.day} ${_months[d.month - 1]}';
}

/// A person's name from a `{id, full_name}` the server sent, or null.
String? _personName(Object? ref) {
  final n = ref is Map ? (ref['full_name'] as String?)?.trim() : null;
  return n == null || n.isEmpty ? null : n;
}

/// AND-SUPERVISOR-011: the project's weekly reports. Open one to read the AI draft.
class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key, required this.projectId, this.projectTitle});
  final String projectId;
  final String? projectTitle;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reports = ref.watch(reportsProvider(projectId));
    return Scaffold(
      appBar: IbhAppBar(title: 'Weekly reports', subtitle: projectTitle),
      body: reports.when(
        loading: () => const SkeletonList(rows: 3),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(reportsProvider(projectId))),
        data: (items) => items.isEmpty
            ? const EmptyState(
                icon: Icons.description_outlined,
                title: 'No reports yet',
                message: 'The first draft is made on Friday. You\'ll review it here before the client sees it.',
              )
            : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                IbhGroup(children: [
                  for (final r in items)
                    IbhRow(
                      title: 'Week of ${_weekOf(r['week_start'] as String)}',
                      subtitle: 'AI-generated',
                      trailing: StatusChip(_reportChip(r['status'] as String).label, tone: _reportChip(r['status'] as String).tone),
                      onTap: () async {
                        await Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ReportScreen(report: r, projectId: projectId, projectTitle: projectTitle)));
                        ref.invalidate(reportsProvider(projectId));
                      },
                    ),
                ]),
              ]),
      ),
    );
  }
}

/// One weekly report: read the AI draft, add a note to the client under your own name, and mark it reviewed
/// so it is sent.
///
/// The AI's text is never edited here or on the server: the supervisor's own words are the note, shown under
/// their name. The report is labelled AI-generated (and "Reviewed by" once it is), lists the evidence it
/// used, and takes money figures from the ledger, never from the model. Reviewing cannot approve, release or pay.
class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key, required this.report, required this.projectId, this.projectTitle});
  final Map<String, dynamic> report;
  final String projectId;
  final String? projectTitle;

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  late Map<String, dynamic> _report = widget.report;
  bool _busy = false;

  String? get _note => (_report['supervisor_note'] as String?)?.trim().isEmpty ?? true ? null : _report['supervisor_note'] as String;

  Future<void> _editNote() async {
    final updated = await Navigator.of(context).push<Map<String, dynamic>>(MaterialPageRoute(builder: (_) => ReportNoteScreen(report: _report)));
    if (updated != null && mounted) {
      setState(() => _report = updated);
      ref.invalidate(reportsProvider(widget.projectId));
    }
  }

  Future<void> _review() async {
    final cited = ((_report['evidence_ids'] as List?) ?? const []).length;
    final me = ref.read(authProvider).me?['full_name'] as String?;
    final go = await confirmSheet(
      context,
      title: 'Mark the report reviewed?',
      message: 'It is sent to the client within 15 minutes, on WhatsApp and email, labelled AI-generated and '
          'reviewed by ${me == null || me.trim().isEmpty ? 'you' : me}. Check every sentence against what you saw first.\n\n'
          'Your note: ${_note == null ? 'none' : 'added'}\nEvidence cited: $cited',
      confirmLabel: 'Mark reviewed',
      cancelLabel: 'Keep reading',
    );
    if (!go || !mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/reports/${_report['id']}/review',
        idempotencyKey: 'report-${_report['id']}',
      );
      ref.invalidate(reportsProvider(widget.projectId));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Reviewed. The report is on its way to the client.')));
      Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = _report;
    final status = r['status'] as String;
    final evidence = ((r['evidence_ids'] as List?) ?? const []).cast<String>();
    final chip = _reportChip(status);
    final reviewer = _personName(r['reviewed_by']);
    final noteBy = _personName(r['note_by']);
    return Scaffold(
      appBar: IbhAppBar(
        title: 'Weekly report',
        subtitle: '${widget.projectTitle == null ? '' : '${widget.projectTitle} · '}week of ${_weekOf(r['week_start'] as String)}',
      ),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
          const StatusChip('AI-generated draft', tone: ChipTone.info),
          StatusChip(chip.label, tone: chip.tone),
          if (reviewer != null) StatusChip('Reviewed by $reviewer', tone: ChipTone.ok),
        ]),
        const SizedBox(height: IbhSpace.s12),
        Text('Written by iBackHome\'s report assistant from this week\'s project data. Check every sentence against what you saw.',
            style: IbhText.small.copyWith(color: IbhColors.muted)),
        const SizedBox(height: IbhSpace.s12),
        IbhCard(child: MarkdownLite('${r['body_md']}')),
        if (_note != null) ...[
          const SizedBox(height: IbhSpace.s12),
          IbhCard(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Note from ${noteBy ?? 'your supervisor'}', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
              const SizedBox(height: IbhSpace.s4),
              Text(_note!, style: IbhText.body),
            ]),
          ),
        ],
        if (evidence.isNotEmpty) ...[
          const IbhSectionLabel('EVIDENCE USED'),
          Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
            for (final e in evidence)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(color: IbhColors.mist, borderRadius: BorderRadius.circular(IbhRadius.tag), border: Border.all(color: IbhColors.line)),
                child: Text('EV-${e.substring(0, 4).toUpperCase()}', style: IbhText.mono.copyWith(fontSize: 12)),
              ),
          ]),
        ],
        const SizedBox(height: IbhSpace.s12),
        Text('Money figures come from the ledger. Held by a licensed escrow partner, never by iBackHome.', style: IbhText.small.copyWith(color: IbhColors.muted)),
      ]),
      bottomNavigationBar: status == 'draft'
          ? BottomActionBar(row: true, children: [
              OutlinedButton.icon(
                onPressed: _busy ? null : _editNote,
                icon: const Icon(Icons.edit_note),
                label: Text(_note == null ? 'Add a note' : 'Edit note'),
              ),
              FilledButton(onPressed: _busy ? null : _review, child: const Text('Mark reviewed')),
            ])
          : null,
    );
  }
}

/// AND-SUPERVISOR-011, "Edit report": your note to the client, shown under your name. The AI's text and the
/// money lines are read-only (the money comes straight from the ledger).
class ReportNoteScreen extends ConsumerStatefulWidget {
  const ReportNoteScreen({super.key, required this.report});
  final Map<String, dynamic> report;

  @override
  ConsumerState<ReportNoteScreen> createState() => _ReportNoteScreenState();
}

class _ReportNoteScreenState extends ConsumerState<ReportNoteScreen> {
  static const maxChars = 2000;
  late final _note = TextEditingController(text: widget.report['supervisor_note'] as String? ?? '');
  bool _busy = false;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final updated = await ref.read(servicesProvider).api.patch<Map<String, dynamic>>(
        '/reports/${widget.report['id']}',
        body: {'supervisor_note': _note.text},
      );
      if (mounted) Navigator.of(context).pop(updated);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(
          title: 'Add a note',
          subtitle: 'Shown under your name',
          leading: IbhBarLeading.close,
          actions: [TextButton(onPressed: _busy ? null : _save, child: const Text('Save', style: TextStyle(fontWeight: FontWeight.w700)))],
        ),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          Container(
            padding: const EdgeInsets.all(IbhSpace.s16),
            decoration: BoxDecoration(color: IbhColors.neutralBg, borderRadius: BorderRadius.circular(IbhRadius.card)),
            child: const Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.lock_outline, size: 20),
              SizedBox(width: IbhSpace.s12),
              Expanded(
                child: Text(
                  'The report text comes from iBackHome\'s assistant, and the money lines straight from the ledger. You can\'t edit them. Your note goes under your name.',
                  style: IbhText.body,
                ),
              ),
            ]),
          ),
          const SizedBox(height: IbhSpace.s16),
          Text.rich(TextSpan(style: IbhText.body.copyWith(fontWeight: FontWeight.w600, color: IbhColors.ink), children: [
            const TextSpan(text: 'Your note to the client '),
            TextSpan(text: '(optional)', style: IbhText.small.copyWith(color: IbhColors.muted)),
          ])),
          const SizedBox(height: IbhSpace.s8),
          TextField(
            controller: _note,
            maxLines: 6,
            maxLength: maxChars,
            textCapitalization: TextCapitalization.sentences,
            autofocus: true,
          ),
          const SizedBox(height: IbhSpace.s8),
          Text('Leave it empty and save to remove your note.', style: IbhText.small.copyWith(color: IbhColors.muted)),
        ]),
      );
}
