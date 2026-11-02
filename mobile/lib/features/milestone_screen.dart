import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/money.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/sheets.dart';
import '../ui/states.dart';
import 'capture_target.dart';
import 'project_screen.dart';
import 'projects_tab.dart';
import 'verify_screen.dart';
import 'widgets.dart';

/// One milestone. A supervisor sees its checklist and starts the visit or verifies it
/// (AND-SUPERVISOR-004); a contractor sees what the supervisor will capture, what they get on
/// release, and claims it (AND-CONTRACTOR-002).
class MilestoneScreen extends ConsumerStatefulWidget {
  const MilestoneScreen({super.key, required this.projectId, required this.milestoneId});

  final String projectId;
  final String milestoneId;

  @override
  ConsumerState<MilestoneScreen> createState() => _MilestoneScreenState();
}

class _MilestoneScreenState extends ConsumerState<MilestoneScreen> {
  late final Services _s = ref.read(servicesProvider);
  List<QueuedCapture> _mine = const [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _s.sync.addListener(_loadLocal);
    _loadLocal();
  }

  @override
  void dispose() {
    _s.sync.removeListener(_loadLocal);
    super.dispose();
  }

  /// This phone's captures for the milestone (what the supervisor has already taken).
  Future<void> _loadLocal() async {
    final all = await _s.db.all(projectId: widget.projectId);
    if (!mounted) return;
    setState(() => _mine = all.where((c) => c.milestoneId == widget.milestoneId && !c.asContractor && c.status != CaptureStatus.draft).toList());
  }

  Future<void> _claim(String name) async {
    final go = await confirmSheet(
      context,
      title: 'Claim $name?',
      message: 'The supervisor will be asked to visit the site and check the work. You can add photos before or after.',
      confirmLabel: 'Claim milestone',
    );
    if (!go || !mounted) return;
    setState(() => _busy = true);
    try {
      final sent = await _s.sendOrQueue(
        kind: 'claim',
        path: '/milestones/${widget.milestoneId}/claim',
        label: 'Claim $name',
        projectId: widget.projectId,
      );
      ref.invalidate(projectProvider(widget.projectId));
      ref.invalidate(projectMilestonesProvider(widget.projectId));
      if (!mounted) return;
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(
            content: Text(sent
                ? '$name claimed. The supervisor has been asked to visit.'
                : 'No signal. Your claim is saved and will be sent when you are back online.')));
      Navigator.of(context).pop();
    } catch (e) {
      // A 409 means the milestone changed; nothing was done twice.
      if (mounted) showError(context, e);
      ref.invalidate(projectProvider(widget.projectId));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = ref.watch(projectProvider(widget.projectId));
    final auth = ref.watch(authProvider);
    return data.when(
      loading: () => const Scaffold(appBar: IbhAppBar(title: 'Milestone'), body: SkeletonList(rows: 3)),
      error: (e, _) => isRotatedOff(e)
          ? const NotOnProjectPage()
          : Scaffold(
              appBar: const IbhAppBar(title: 'Milestone'),
              body: ErrorRetry(e, () => ref.invalidate(projectProvider(widget.projectId))),
            ),
      data: (d) {
        final m = d.milestones.where((x) => x['id'] == widget.milestoneId).firstOrNull;
        if (m == null) {
          return const Scaffold(appBar: IbhAppBar(title: 'Milestone'), body: EmptyState(icon: Icons.lock_outline, title: 'Milestone not found', message: 'It may have been removed. Go back and refresh the project.'));
        }
        return auth.isSupervisor ? _supervisor(d, m) : _contractor(d, m);
      },
    );
  }

  Widget _chip(Map<String, dynamic> m) => StatusChip(milestoneLabel('${m['status']}'), tone: milestoneTone('${m['status']}'));

  Widget? _sentBack(Map<String, dynamic> m) {
    final v = m['latest_verification'] as Map?;
    if (m['status'] == 'funded' && v?['decision'] == 'rejected') {
      return Padding(
        padding: const EdgeInsets.only(bottom: IbhSpace.s12),
        child: Alert('Sent back: ${v!['notes']}', tone: ChipTone.bad),
      );
    }
    return null;
  }

  Widget _supervisor(ProjectData d, Map<String, dynamic> m) {
    final name = '${m['name']}';
    final claimedAt = m['claimed_at'] as String?;
    final captured = defaultChecklist.where((item) => _mine.any((c) => c.checklistItem == item)).length;
    final active = d.project['status'] == 'active';
    final canAct = active && m['status'] == 'claimed';
    return Scaffold(
      appBar: IbhAppBar(
        title: '$name checklist',
        subtitle: '${d.project['title']}${claimedAt == null ? '' : ' · claimed ${watDay(DateTime.parse(claimedAt))}'}',
      ),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Row(children: [
          Expanded(child: Text('$captured of ${defaultChecklist.length} captured', style: IbhText.h3.copyWith(fontSize: 18))),
          _chip(m),
        ]),
        const SizedBox(height: IbhSpace.s12),
        ?_sentBack(m),
        IbhGroup(children: [
          for (var i = 0; i < defaultChecklist.length; i++) _ChecklistRow(i + 1, defaultChecklist[i], _mine.where((c) => c.checklistItem == defaultChecklist[i]).length),
        ]),
        const SizedBox(height: IbhSpace.s12),
        Text(
          m['status'] == 'released'
              ? 'This milestone is released. You can view it but not change it.'
              : 'Take at least one photo for each item, then verify. A release also needs the client\'s approval.',
          style: IbhText.small.copyWith(color: IbhColors.muted),
        ),
      ]),
      bottomNavigationBar: canAct
          ? BottomActionBar(children: [
              FilledButton(onPressed: () => startVisit(context, ref, d, m), child: const Text('Start visit')),
              OutlinedButton(
                onPressed: () async {
                  final done = await Navigator.of(context).push<bool>(MaterialPageRoute(
                      builder: (_) => VerifyScreen(projectId: widget.projectId, milestoneId: m['id'] as String, milestoneName: name, projectTitle: '${d.project['title']}', sequence: m['sequence'] as int)));
                  if (done == true) {
                    ref.invalidate(projectProvider(widget.projectId));
                    ref.invalidate(projectMilestonesProvider(widget.projectId));
                    if (mounted) Navigator.of(context).pop();
                  }
                },
                child: Text('Verify $name'),
              ),
            ])
          : null,
    );
  }

  Widget _contractor(ProjectData d, Map<String, dynamic> m) {
    final name = '${m['name']}';
    final total = d.milestones.length;
    final canClaim = d.project['status'] == 'active' && m['status'] == 'funded';
    return Scaffold(
      appBar: IbhAppBar(title: name, subtitle: '${d.project['title']} · ${m['sequence']} of $total', actions: [
        Padding(padding: const EdgeInsets.only(right: IbhSpace.s16), child: _chip(m)),
      ]),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        IbhCard(
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('For you on release', style: IbhText.body),
            Text(formatMoney(m['amount_minor'] as int, currency: '${m['currency']}'), style: IbhText.h3.copyWith(fontSize: 20)),
          ]),
        ),
        const SizedBox(height: IbhSpace.s4),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: IbhSpace.s8),
          child: Text('Held by a licensed escrow partner, never by iBackHome.', style: IbhText.small.copyWith(color: IbhColors.muted)),
        ),
        ?_sentBack(m),
        const IbhSectionLabel('WHAT THE SUPERVISOR WILL CAPTURE'),
        IbhGroup(children: [
          for (var i = 0; i < defaultChecklist.length; i++) _ChecklistRow(i + 1, defaultChecklist[i], 0, simple: true),
        ]),
        const SizedBox(height: IbhSpace.s16),
        OutlinedButton.icon(
          icon: const Icon(Icons.photo_camera_outlined),
          label: const Text('Add contractor photo'),
          onPressed: () => startVisit(context, ref, d, m, asContractor: true),
        ),
        const SizedBox(height: IbhSpace.s8),
        Text('Your photos are labelled as the contractor\'s and do not count toward verification.', style: IbhText.small.copyWith(color: IbhColors.muted)),
      ]),
      bottomNavigationBar: canClaim
          ? BottomActionBar(children: [
              FilledButton(onPressed: _busy ? null : () => _claim(name), child: const Text('Claim milestone')),
            ])
          : null,
    );
  }
}

/// A numbered checklist row: the number in a dashed box (a tick once it has a capture).
class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow(this.number, this.text, this.captures, {this.simple = false});

  final int number;
  final String text;
  final int captures;
  final bool simple;

  @override
  Widget build(BuildContext context) {
    final done = captures > 0;
    return IbhRow(
      title: text,
      titleStyle: IbhText.body.copyWith(fontWeight: simple ? FontWeight.w400 : FontWeight.w600, color: IbhColors.ink),
      subtitle: simple ? null : (done ? '$captures captured' : 'Not captured yet'),
      leading: Container(
        width: 28,
        height: 28,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: done ? IbhColors.navy900 : null,
          borderRadius: BorderRadius.circular(IbhRadius.tag),
          border: Border.all(color: done ? IbhColors.navy900 : IbhColors.placeholderBorder),
        ),
        child: done
            ? const Icon(Icons.check, size: 18, color: IbhColors.white)
            : Text('$number', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: IbhColors.muted)),
      ),
    );
  }
}
