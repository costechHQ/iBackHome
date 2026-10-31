import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'home_screen.dart';
import 'permissions_screen.dart';
import 'project_screen.dart';
import 'widgets.dart';

/// A project's milestones, newest data from the server (`GET /projects/{id}/milestones`).
final projectMilestonesProvider = FutureProvider.autoDispose.family<List<Map<String, dynamic>>, String>((ref, id) async {
  final ms = await ref.read(servicesProvider).api.get<List<dynamic>>('/projects/$id/milestones');
  return ms.cast<Map<String, dynamic>>()..sort((a, b) => (a['sequence'] as int).compareTo(b['sequence'] as int));
});

String _greeting() {
  final h = toWat(DateTime.now()).hour;
  return h < 12 ? 'Good morning' : (h < 17 ? 'Good afternoon' : 'Good evening');
}

({String label, ChipTone tone}) projectChip(String status) => switch (status) {
      'active' => (label: 'Active', tone: ChipTone.info),
      'boq_review' => (label: 'BoQ review', tone: ChipTone.warn),
      'draft' => (label: 'Draft', tone: ChipTone.neutral),
      'paused' => (label: 'Paused', tone: ChipTone.neutral),
      'completed' => (label: 'Completed', tone: ChipTone.ok),
      _ => (label: status, tone: ChipTone.neutral),
    };

Map<String, dynamic>? _firstWhere(List<Map<String, dynamic>> ms, String status) {
  for (final m in ms) {
    if (m['status'] == status) return m;
  }
  return null;
}

/// AND-SUPERVISOR-004 and AND-CONTRACTOR-002: the project list. A supervisor sees today's visit first;
/// a contractor sees where each project stands and what to do next.
class ProjectsTab extends ConsumerWidget {
  const ProjectsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final projects = ref.watch(projectsProvider);
    final device = ref.watch(deviceProvider);
    final auth = ref.watch(authProvider);
    final supervisor = auth.isSupervisor;
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(projectMilestonesProvider);
        await ref.refresh(projectsProvider.future); // ignore: unused_result
      },
      child: projects.when(
        loading: () => const SkeletonList(),
        error: (e, _) => ListView(children: [SizedBox(height: 320, child: ErrorRetry(e, () => ref.invalidate(projectsProvider)))]),
        data: (items) {
          if (items.isEmpty) {
            return ListView(children: [
              SizedBox(
                height: 420,
                child: supervisor
                    ? const EmptyState(
                        icon: Icons.fact_check_outlined,
                        title: 'No projects assigned',
                        message: 'iBackHome will assign you and tell you by SMS.',
                      )
                    : const EmptyState(
                        icon: Icons.home_work_outlined,
                        title: 'No projects yet',
                        message: 'A project appears here once a client invites you to it.',
                      ),
              ),
            ]);
          }
          final ms = {for (final p in items) p['id'] as String: ref.watch(projectMilestonesProvider(p['id'] as String)).value};
          return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
            if (device.hasError) _DeviceAlert(device.error!),
            if (!supervisor) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                child: Text(
                  '${_greeting()}${_first(auth.me?['full_name']) == null ? '' : ', ${_first(auth.me?['full_name'])}'}',
                  style: IbhText.bodyLg,
                ),
              ),
            ],
            if (supervisor) ..._today(context, items, ms),
            if (supervisor)
              IbhGroup(children: [for (final p in items) _SupervisorRow(project: p, milestones: ms[p['id']])])
            else
              for (final p in items)
                Padding(
                  padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                  child: _ContractorCard(project: p, milestones: ms[p['id']]),
                ),
            const SizedBox(height: IbhSpace.s16),
            Text(
              supervisor
                  ? 'You supervise each project for two milestones, then iBackHome rotates you.'
                  : 'BoQ editing and payouts are on the web portal. The app is for the site.',
              style: IbhText.small.copyWith(color: IbhColors.muted),
            ),
          ]);
        },
      ),
    );
  }

  static String? _first(Object? name) {
    final s = (name as String?)?.trim();
    return s == null || s.isEmpty ? null : s.split(' ').first;
  }

  /// The "Today" card: the first project with a claimed milestone waiting for this supervisor.
  List<Widget> _today(BuildContext context, List<Map<String, dynamic>> items, Map<String, List<Map<String, dynamic>>?> ms) {
    for (final p in items) {
      final claimed = ms[p['id']] == null ? null : _firstWhere(ms[p['id']]!, 'claimed');
      if (claimed == null) continue;
      final at = claimed['claimed_at'] as String?;
      return [
        IbhCard(
          emphasis: true,
          onTap: () => _open(context, p),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('TODAY', style: IbhText.caption.copyWith(color: IbhColors.muted)),
            const SizedBox(height: IbhSpace.s4),
            Text('Visit ${p['title']}', style: IbhText.h3.copyWith(fontSize: 18)),
            const SizedBox(height: IbhSpace.s4),
            Text(
              '${claimed['name']} was claimed${at == null ? '' : ' ${watDay(DateTime.parse(at))}'}. Check it on site.',
              style: IbhText.body,
            ),
          ]),
        ),
        const SizedBox(height: IbhSpace.s12),
      ];
    }
    return const [];
  }

  static void _open(BuildContext context, Map<String, dynamic> p) => Navigator.of(context)
      .push(MaterialPageRoute<void>(builder: (_) => ProjectScreen(projectId: p['id'] as String)));
}

class _DeviceAlert extends ConsumerWidget {
  const _DeviceAlert(this.error);
  final Object error;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final revoked = ApiError.from(error).code == 'device_revoked_here';
    return Padding(
      padding: const EdgeInsets.only(bottom: IbhSpace.s12),
      child: Column(children: [
        Alert('This phone is not registered yet, so you cannot capture. ${ApiError.from(error).message}', tone: ChipTone.bad),
        TextButton(
          onPressed: () async {
            if (revoked) {
              await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const PermissionsScreen()));
            }
            ref.invalidate(deviceProvider);
          },
          child: const Text('Register this phone'),
        ),
      ]),
    );
  }
}

class _SupervisorRow extends StatelessWidget {
  const _SupervisorRow({required this.project, required this.milestones});
  final Map<String, dynamic> project;
  final List<Map<String, dynamic>>? milestones;

  @override
  Widget build(BuildContext context) {
    final claimed = milestones == null ? null : _firstWhere(milestones!, 'claimed');
    final current = claimed ?? (milestones == null ? null : (_firstWhere(milestones!, 'funded') ?? _firstWhere(milestones!, 'pending')));
    final status = project['status'] as String;
    final (label, tone) = claimed != null
        ? ('Visit today', ChipTone.warn)
        : current != null
            ? (milestoneLabel('${current['status']}'), milestoneTone('${current['status']}'))
            : (projectChip(status).label, projectChip(status).tone);
    return IbhRow(
      title: '${project['title']}',
      subtitle: '${project['address']}${current == null ? '' : ' · ${current['name']}'}',
      trailing: StatusChip(label, tone: tone),
      onTap: () => ProjectsTab._open(context, project),
    );
  }
}

class _ContractorCard extends StatelessWidget {
  const _ContractorCard({required this.project, required this.milestones});
  final Map<String, dynamic> project;
  final List<Map<String, dynamic>>? milestones;

  @override
  Widget build(BuildContext context) {
    final chip = projectChip(project['status'] as String);
    final ms = milestones ?? const [];
    final released = ms.where((m) => m['status'] == 'released').length;
    final progress = ms.isEmpty ? 'not started' : '$released of ${ms.length} released';
    final (action, emphasis) = _next(project['status'] as String, ms);
    return IbhCard(
      onTap: () => ProjectsTab._open(context, project),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: Text('${project['title']}', style: IbhText.h3.copyWith(fontSize: 18))),
          const SizedBox(width: IbhSpace.s8),
          StatusChip(chip.label, tone: chip.tone),
        ]),
        const SizedBox(height: IbhSpace.s4),
        Text('${project['address']} · $progress', style: IbhText.body),
        if (action != null) ...[
          const SizedBox(height: IbhSpace.s8),
          Text(action, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: emphasis ? IbhColors.ink : IbhColors.muted)),
        ],
      ]),
    );
  }

  (String?, bool) _next(String status, List<Map<String, dynamic>> ms) {
    if (status == 'draft' || status == 'boq_review') return ('Waiting for the bill of quantities to be approved on the web portal', false);
    final funded = _firstWhere(ms, 'funded');
    if (funded != null) return ('${funded['name']}: ready to claim ›', true);
    final claimed = _firstWhere(ms, 'claimed');
    if (claimed != null) return ('${claimed['name']}: waiting for the supervisor', false);
    final verified = _firstWhere(ms, 'verified');
    if (verified != null) return ('${verified['name']}: waiting for the client to approve', false);
    return (null, false);
  }
}
