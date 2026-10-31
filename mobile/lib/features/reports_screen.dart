import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'widgets.dart';

final reportsProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>((ref, projectId) async {
  final list = await ref.read(servicesProvider).api.get<List<dynamic>>('/projects/$projectId/reports');
  return list.cast<Map<String, dynamic>>();
});

/// AND-SUPERVISOR-011: read the AI draft and mark it reviewed so it is sent to the client.
///
/// The report is labelled as AI-generated and lists the evidence it used. Money figures in it
/// come from the ledger, never from the model. Reviewing here cannot approve, release or pay.
class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key, required this.projectId});
  final String projectId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final reports = ref.watch(reportsProvider(projectId));
    return Scaffold(
      appBar: AppBar(title: const Text('Weekly reports')),
      body: reports.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(reportsProvider(projectId))),
        data: (items) => items.isEmpty
            ? const Center(child: Padding(padding: EdgeInsets.all(IbhSpace.s32), child: Text('No reports yet. The first draft is made on Friday.')))
            : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
                for (final r in items) _ReportCard(report: r, projectId: projectId),
              ]),
      ),
    );
  }
}

class _ReportCard extends ConsumerStatefulWidget {
  const _ReportCard({required this.report, required this.projectId});
  final Map<String, dynamic> report;
  final String projectId;

  @override
  ConsumerState<_ReportCard> createState() => _ReportCardState();
}

class _ReportCardState extends ConsumerState<_ReportCard> {
  bool _busy = false;

  Future<void> _review() async {
    setState(() => _busy = true);
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/reports/${widget.report['id']}/review',
        idempotencyKey: 'report-${widget.report['id']}',
      );
      ref.invalidate(reportsProvider(widget.projectId));
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
    final evidence = (r['evidence_ids'] as List).cast<String>();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(IbhSpace.s16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('Week of ${r['week_start']}', style: IbhText.h3.copyWith(fontSize: 16))),
            StatusChip(
              switch (status) { 'draft' => 'Needs your review', 'reviewed' => 'Reviewed', _ => 'Sent' },
              tone: status == 'draft' ? ChipTone.warn : ChipTone.ok,
            ),
          ]),
          const SizedBox(height: IbhSpace.s8),
          const StatusChip('AI-generated', tone: ChipTone.info),
          const SizedBox(height: IbhSpace.s12),
          SelectableText(_plain(r['body_md'] as String), style: IbhText.body),
          if (evidence.isNotEmpty) ...[
            const SizedBox(height: IbhSpace.s12),
            Text('Evidence used: ${evidence.map((e) => 'EV-${e.substring(0, 4)}').join(', ')}', style: IbhText.mono.copyWith(fontSize: 11)),
          ],
          const SizedBox(height: IbhSpace.s8),
          const Text('Figures come from the ledger. Funds are held by a licensed escrow partner, never by iBackHome.', style: IbhText.small),
          if (status == 'draft') ...[
            const SizedBox(height: IbhSpace.s12),
            FilledButton(onPressed: _busy ? null : _review, child: const Text('Mark reviewed and send')),
          ],
        ]),
      ),
    );
  }

  /// The report is Markdown; show it as plain text without the markup characters.
  static String _plain(String md) => md
      .replaceAll(RegExp(r'^#+\s*', multiLine: true), '')
      .replaceAll('**', '')
      .replaceAll(RegExp(r'^[-*]\s+', multiLine: true), '• ');
}
