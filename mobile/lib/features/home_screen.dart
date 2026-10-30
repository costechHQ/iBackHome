import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'project_screen.dart';
import 'queue_screen.dart';
import 'widgets.dart';

final projectsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final page = await ref.read(servicesProvider).api.get<Map<String, dynamic>>('/projects', query: {'limit': 50});
  return (page['items'] as List).cast<Map<String, dynamic>>();
});

/// Registers the signing key with the server. Capture is blocked until this succeeds.
final deviceProvider = FutureProvider.autoDispose<String>((ref) => ref.read(servicesProvider).registerDevice());

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final sync = ref.read(servicesProvider).sync;
    return Scaffold(
      appBar: AppBar(title: Text(['Projects', 'Sync queue', 'Me'][_tab])),
      body: [const _ProjectsTab(), const QueueScreen(), const _MeTab()][_tab],
      bottomNavigationBar: ListenableBuilder(
        listenable: sync,
        builder: (_, _) => NavigationBar(
          selectedIndex: _tab,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.home_work_outlined), label: 'Projects'),
            NavigationDestination(icon: Icon(Icons.cloud_upload_outlined), label: 'Queue'),
            NavigationDestination(icon: Icon(Icons.person_outline), label: 'Me'),
          ],
        ),
      ),
    );
  }
}

class _ProjectsTab extends ConsumerWidget {
  const _ProjectsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final projects = ref.watch(projectsProvider);
    final device = ref.watch(deviceProvider);
    return RefreshIndicator(
      onRefresh: () async => ref.refresh(projectsProvider.future),
      child: projects.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(projectsProvider)),
        data: (items) => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          if (device.hasError)
            Padding(
              padding: const EdgeInsets.only(bottom: IbhSpace.s12),
              child: Column(children: [
                Alert('This phone is not registered yet, so you cannot capture. ${ApiError.from(device.error!).message}',
                    tone: ChipTone.bad),
                TextButton(onPressed: () => ref.invalidate(deviceProvider), child: const Text('Register this phone')),
              ]),
            ),
          if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.all(IbhSpace.s32),
              child: Center(child: Text('No projects yet. Operations will assign you to one.')),
            ),
          for (final p in items)
            Card(
              child: ListTile(
                minVerticalPadding: IbhSpace.s12,
                title: Text(p['title'] as String, style: IbhText.h3.copyWith(fontSize: 16)),
                subtitle: Text(p['address'] as String),
                trailing: StatusChip(p['status'] as String,
                    tone: p['status'] == 'active' ? ChipTone.ok : ChipTone.neutral),
                onTap: () => Navigator.of(context)
                    .push(MaterialPageRoute<void>(builder: (_) => ProjectScreen(projectId: p['id'] as String))),
              ),
            ),
        ]),
      ),
    );
  }
}

class _MeTab extends ConsumerWidget {
  const _MeTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final device = ref.watch(deviceProvider);
    final me = auth.me ?? const {};
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      Text('${me['full_name'] ?? 'Your account'}', style: IbhText.h3),
      Text('${me['phone'] ?? me['email'] ?? ''}'),
      const SizedBox(height: IbhSpace.s8),
      StatusChip('${me['role']}', tone: ChipTone.info),
      const Divider(height: IbhSpace.s32),
      const Text('This phone', style: IbhText.h3),
      const SizedBox(height: IbhSpace.s8),
      device.when(
        loading: () => const LinearProgressIndicator(),
        error: (e, _) => Alert(ApiError.from(e).message, tone: ChipTone.bad),
        data: (id) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const StatusChip('Signing key registered', tone: ChipTone.ok),
          const SizedBox(height: IbhSpace.s8),
          Text(id, style: IbhText.mono.copyWith(fontSize: 11)),
        ]),
      ),
      const SizedBox(height: IbhSpace.s32),
      OutlinedButton(
        onPressed: () => confirmSignOut(context, ref),
        child: const Text('Sign out'),
      ),
    ]);
  }
}
