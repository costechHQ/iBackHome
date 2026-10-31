import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/markdown_lite.dart';
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

/// One weekly report: read the AI draft and mark it reviewed so it is sent to the client.
///
/// Review-only (decided): the supervisor can read it and mark it reviewed, not edit it. It is labelled
/// AI-generated, lists the evidence it used, and takes money figures from the ledger, never from
/// the model. Reviewing cannot approve, release or pay.
class ReportScreen extends ConsumerStatefulWidget {
  const ReportScreen({super.key, required this.report, required this.projectId, this.projectTitle});
  final Map<String, dynamic> report;
  final String projectId;
  final String? projectTitle;

  @override
  ConsumerState<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends ConsumerState<ReportScreen> {
  bool _busy = false;

  Future<void> _review() async {
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mark this report reviewed?'),
        content: const Text('The client gets it by WhatsApp and email, labelled AI-generated and reviewed by you. Check every sentence against what you saw first.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Keep reading')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Mark reviewed')),
        ],
      ),
    );
    if (go != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/reports/${widget.report['id']}/review',
        idempotencyKey: 'report-${widget.report['id']}',
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
    final r = widget.report;
    final status = r['status'] as String;
    final evidence = ((r['evidence_ids'] as List?) ?? const []).cast<String>();
    final chip = _reportChip(status);
    return Scaffold(
      appBar: IbhAppBar(
        title: 'Weekly report',
        subtitle: '${widget.projectTitle == null ? '' : '${widget.projectTitle} · '}week of ${_weekOf(r['week_start'] as String)}',
      ),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
          const StatusChip('AI-generated draft', tone: ChipTone.info),
          StatusChip(chip.label, tone: chip.tone),
        ]),
        const SizedBox(height: IbhSpace.s12),
        Text('Written by iBackHome\'s report assistant from this week\'s project data. Check every sentence against what you saw.',
            style: IbhText.small.copyWith(color: IbhColors.muted)),
        const SizedBox(height: IbhSpace.s12),
        IbhCard(child: MarkdownLite('${r['body_md']}')),
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
          ? BottomActionBar(children: [
              FilledButton(onPressed: _busy ? null : _review, child: const Text('Mark reviewed')),
            ])
          : null,
    );
  }
}
