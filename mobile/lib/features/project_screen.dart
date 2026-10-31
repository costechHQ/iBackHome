import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/geo.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'arrival_screen.dart';
import 'capture_target.dart';
import 'milestone_screen.dart';
import 'permissions_screen.dart';
import 'projects_tab.dart';
import 'reports_screen.dart';
import 'widgets.dart';

class ProjectData {
  ProjectData(this.project, this.milestones);
  final Map<String, dynamic> project;
  final List<Map<String, dynamic>> milestones;

  List<List<double>>? get fence {
    final site = project['site'] as Map<String, dynamic>?;
    return site == null ? null : Geo.ringFrom((site['geofence'] as Map).cast<String, dynamic>());
  }

  Map<String, dynamic>? get claimed {
    for (final m in milestones) {
      if (m['status'] == 'claimed') return m;
    }
    return null;
  }
}

final projectProvider = FutureProvider.autoDispose.family<ProjectData, String>((ref, id) async {
  final api = ref.read(servicesProvider).api;
  final project = await api.get<Map<String, dynamic>>('/projects/$id');
  final ms = await api.get<List<dynamic>>('/projects/$id/milestones');
  final list = ms.cast<Map<String, dynamic>>()..sort((a, b) => (a['sequence'] as int).compareTo(b['sequence'] as int));
  return ProjectData(project, list);
});

/// Starts the arrival check for a capture: makes sure the phone is set up, then opens the arrival
/// screen with the project's site boundary.
Future<void> startVisit(BuildContext context, WidgetRef ref, ProjectData d, Map<String, dynamic> m, {bool asContractor = false}) async {
  if (!await ensureCaptureReady(context, ref) || !context.mounted) return;
  await Navigator.of(context).push(MaterialPageRoute<void>(
    builder: (_) => ArrivalScreen(
      target: CaptureTarget(
        projectId: d.project['id'] as String,
        milestoneId: m['id'] as String,
        title: '${m['name']}',
        subtitle: d.project['title'] as String?,
        fence: d.fence,
        asContractor: asContractor,
      ),
    ),
  ));
}

/// AND-SUPERVISOR-004 "Project detail": the project's milestones, one row each; open one for its
/// checklist (supervisor) or to claim it (contractor).
class ProjectScreen extends ConsumerWidget {
  const ProjectScreen({super.key, required this.projectId});
  final String projectId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(projectProvider(projectId));
    final auth = ref.watch(authProvider);
    final d = data.value;
    final claimed = d?.claimed;
    final canVisit = auth.isSupervisor && d != null && claimed != null && d.project['status'] == 'active';
    return Scaffold(
      appBar: IbhAppBar(title: d?.project['title'] as String? ?? 'Project', subtitle: d?.project['address'] as String?),
      body: data.when(
        loading: () => const SkeletonList(),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(projectProvider(projectId))),
        data: (d) => RefreshIndicator(
          onRefresh: () async => ref.refresh(projectProvider(projectId).future),
          child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
            if (d.project['site'] == null)
              const Padding(
                padding: EdgeInsets.only(bottom: IbhSpace.s12),
                child: Alert('The site has no boundary yet, so captures will be flagged for review.'),
              ),
            if (const {'draft', 'boq_review'}.contains(d.project['status']))
              Padding(
                padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                child: Alert(
                  auth.isContractor
                      ? 'Waiting for the bill of quantities to be approved. Submit it on the iBackHome website; the milestones appear here once the client, you and operations have approved it.'
                      : 'This project is still being set up. Milestones appear once the bill of quantities is approved.',
                  tone: ChipTone.info,
                ),
              )
            else if (d.project['status'] != 'active')
              Padding(
                padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                child: Alert('This project is ${d.project['status']}: claims, verification and approvals are on hold.', tone: ChipTone.info),
              ),
            if (auth.isSupervisor)
              Padding(
                padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                child: IbhGroup(children: [
                  IbhRow(
                    title: 'Weekly reports',
                    subtitle: 'Read the AI draft and mark it reviewed',
                    leading: const Icon(Icons.description_outlined),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => ReportsScreen(projectId: projectId))),
                  ),
                ]),
              ),
            if (d.milestones.isEmpty)
              const IbhCard(child: Text('No milestones yet.', style: IbhText.body))
            else
              IbhGroup(children: [
                for (final m in d.milestones)
                  IbhRow(
                    title: '${m['sequence']} · ${m['name']}',
                    trailing: StatusChip(milestoneLabel('${m['status']}'), tone: milestoneTone('${m['status']}')),
                    onTap: () async {
                      await Navigator.of(context).push(MaterialPageRoute<void>(
                          builder: (_) => MilestoneScreen(projectId: projectId, milestoneId: m['id'] as String)));
                      ref.invalidate(projectMilestonesProvider(projectId));
                    },
                  ),
              ]),
            const SizedBox(height: IbhSpace.s16),
            Text(
              auth.isSupervisor
                  ? 'Released milestones are read-only. You can only act on milestones assigned to you.'
                  : 'Open a milestone to see what the supervisor will capture, and to claim it when it is funded.',
              style: IbhText.small.copyWith(color: IbhColors.muted),
            ),
          ]),
        ),
      ),
      bottomNavigationBar: canVisit
          ? BottomActionBar(children: [
              FilledButton(onPressed: () => startVisit(context, ref, d, claimed), child: Text('Start ${claimed['name']} visit')),
            ])
          : null,
    );
  }
}
