import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/geo.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'arrival_screen.dart';
import 'capture_target.dart';
import 'permissions_screen.dart';
import 'reports_screen.dart';
import 'verify_screen.dart';
import 'widgets.dart';

class ProjectData {
  ProjectData(this.project, this.milestones);
  final Map<String, dynamic> project;
  final List<Map<String, dynamic>> milestones;

  List<List<double>>? get fence {
    final site = project['site'] as Map<String, dynamic>?;
    return site == null ? null : Geo.ringFrom((site['geofence'] as Map).cast<String, dynamic>());
  }
}

final projectProvider = FutureProvider.autoDispose.family<ProjectData, String>((ref, id) async {
  final api = ref.read(servicesProvider).api;
  final project = await api.get<Map<String, dynamic>>('/projects/$id');
  final ms = await api.get<List<dynamic>>('/projects/$id/milestones');
  return ProjectData(project, ms.cast<Map<String, dynamic>>());
});

/// AND-SUPERVISOR-004: the project's milestones, with capture, claim and verify actions.
class ProjectScreen extends ConsumerWidget {
  const ProjectScreen({super.key, required this.projectId});
  final String projectId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final data = ref.watch(projectProvider(projectId));
    final auth = ref.watch(authProvider);
    return Scaffold(
      appBar: AppBar(title: Text(data.value?.project['title'] as String? ?? 'Project')),
      body: data.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(projectProvider(projectId))),
        data: (d) => RefreshIndicator(
          onRefresh: () async => ref.refresh(projectProvider(projectId).future),
          child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
            Text(d.project['address'] as String),
            const SizedBox(height: IbhSpace.s8),
            if (d.project['site'] == null)
              const Alert('The site has no geofence yet, so captures will be flagged for review.'),
            if (d.project['status'] != 'active')
              Alert('This project is ${d.project['status']}: milestone actions are paused.', tone: ChipTone.info),
            if (auth.isSupervisor)
              Padding(
                padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.description_outlined),
                  label: const Text('Weekly reports'),
                  onPressed: () => Navigator.of(context)
                      .push(MaterialPageRoute<void>(builder: (_) => ReportsScreen(projectId: projectId))),
                ),
              ),
            const SizedBox(height: IbhSpace.s16),
            for (final m in d.milestones)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(IbhSpace.s16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text('${m['sequence']}. ${m['name']}', style: IbhText.h3.copyWith(fontSize: 16))),
                      StatusChip('${m['status']}', tone: milestoneTone('${m['status']}')),
                    ]),
                    if ((m['latest_verification'] as Map?)?['decision'] == 'rejected') ...[
                      const SizedBox(height: IbhSpace.s8),
                      Alert('Sent back: ${(m['latest_verification'] as Map)['notes']}', tone: ChipTone.bad),
                    ],
                    const SizedBox(height: IbhSpace.s12),
                    Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
                      OutlinedButton.icon(
                        icon: const Icon(Icons.photo_camera_outlined),
                        label: const Text('Capture'),
                        onPressed: () async {
                          if (!await ensureCaptureReady(context, ref) || !context.mounted) return;
                          await Navigator.of(context).push(MaterialPageRoute<void>(
                            builder: (_) => ArrivalScreen(
                              target: CaptureTarget(
                                projectId: projectId,
                                milestoneId: m['id'] as String,
                                title: '${m['sequence']}. ${m['name']}',
                                fence: d.fence,
                                asContractor: auth.isContractor,
                              ),
                            ),
                          ));
                        },
                      ),
                      if (auth.isContractor && m['status'] == 'funded')
                        FilledButton(onPressed: () => _claim(context, ref, m['id'] as String, m['name'] as String), child: const Text('Claim')),
                      if (auth.isSupervisor && m['status'] == 'claimed')
                        FilledButton(
                          child: const Text('Verify'),
                          onPressed: () async {
                            final done = await Navigator.of(context).push<bool>(MaterialPageRoute(
                                builder: (_) => VerifyScreen(
                                    projectId: projectId,
                                    milestoneId: m['id'] as String,
                                    milestoneName: m['name'] as String)));
                            if (done == true) ref.invalidate(projectProvider(projectId));
                          },
                        ),
                    ]),
                  ]),
                ),
              ),
          ]),
        ),
      ),
    );
  }

  Future<void> _claim(BuildContext context, WidgetRef ref, String milestoneId, String name) async {
    try {
      final sent = await ref.read(servicesProvider).sendOrQueue(
            kind: 'claim',
            path: '/milestones/$milestoneId/claim',
            label: 'Claim $name',
            projectId: projectId,
          );
      ref.invalidate(projectProvider(projectId));
      if (!sent && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('No signal. Your claim is saved and will be sent when you are back online.')));
      }
    } catch (e) {
      // A 409 means the milestone is no longer fundable-to-claim (it changed); nothing was done.
      if (context.mounted) showError(context, e);
      ref.invalidate(projectProvider(projectId));
    }
  }
}
