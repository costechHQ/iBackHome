import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'permissions_screen.dart';
import 'profile_screen.dart';
import 'project_screen.dart';
import 'queue_screen.dart';
import 'spot_checks_screen.dart';
import 'vetting_screen.dart';
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
    final supervisor = ref.watch(authProvider).isSupervisor;
    final sync = ref.read(servicesProvider).sync;
    // Supervisors also get spot checks; contractors do not do them.
    final tabs = <(String, IconData, Widget)>[
      ('Projects', Icons.home_work_outlined, const VettingGate(child: _ProjectsTab())),
      if (supervisor) ('Spot checks', Icons.pin_drop_outlined, const VettingGate(child: SpotChecksScreen())),
      ('Queue', Icons.cloud_upload_outlined, const QueueScreen()),
      ('Me', Icons.person_outline, const _MeTab()),
    ];
    final i = _tab.clamp(0, tabs.length - 1);
    return Scaffold(
      appBar: AppBar(title: Text(tabs[i].$1)),
      body: tabs[i].$3,
      bottomNavigationBar: ListenableBuilder(
        listenable: sync,
        builder: (_, _) => NavigationBar(
          selectedIndex: i,
          onDestinationSelected: (v) => setState(() => _tab = v),
          destinations: [for (final t in tabs) NavigationDestination(icon: Icon(t.$2), label: t.$1)],
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
                TextButton(
                    onPressed: () async {
                      if (ApiError.from(device.error!).code == 'device_revoked_here') {
                        await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const PermissionsScreen()));
                      }
                      ref.invalidate(deviceProvider);
                    },
                    child: const Text('Register this phone')),
              ]),
            ),
          if (items.isEmpty)
            const Padding(
              padding: EdgeInsets.all(IbhSpace.s32),
              child: Center(child: Text('No projects yet. Operations will assign you to one.', textAlign: TextAlign.center)),
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
    final s = ref.read(servicesProvider);
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      Text('${me['full_name'] ?? 'Your account'}', style: IbhText.h3),
      Text('${me['phone'] ?? me['email'] ?? ''}'),
      const SizedBox(height: IbhSpace.s8),
      StatusChip('${me['role']}', tone: ChipTone.info),
      const SizedBox(height: IbhSpace.s8),
      OutlinedButton(
        onPressed: () =>
            Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ProfileScreen())),
        child: const Text('View and edit profile'),
      ),
      if (auth.isSupervisor) ...[
        const SizedBox(height: IbhSpace.s8),
        ref.watch(vettingProvider).maybeWhen(
              data: (p) => p == null
                  ? const StatusChip('Not applied for vetting', tone: ChipTone.warn)
                  : StatusChip('Vetting: ${p['vetting_status']}',
                      tone: p['vetting_status'] == 'approved' ? ChipTone.ok : ChipTone.warn),
              orElse: () => const SizedBox.shrink(),
            ),
      ],
      const Divider(height: IbhSpace.s32),
      const Text('This phone', style: IbhText.h3),
      const SizedBox(height: IbhSpace.s8),
      device.when(
        loading: () => const LinearProgressIndicator(),
        error: (e, _) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (ApiError.from(e).code == 'device_revoked_here') ...[
            const StatusChip('Signing key revoked', tone: ChipTone.bad),
            const SizedBox(height: IbhSpace.s8),
            Text(ApiError.from(e).message),
            const SizedBox(height: IbhSpace.s8),
            FilledButton(
              onPressed: () async {
                await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const PermissionsScreen()));
                ref.invalidate(deviceProvider);
              },
              child: const Text('Set up this phone again'),
            ),
          ] else ...[
            Alert(ApiError.from(e).message, tone: ChipTone.bad),
            TextButton(onPressed: () => ref.invalidate(deviceProvider), child: const Text('Try again')),
          ],
        ]),
        data: (id) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const StatusChip('Signing key registered', tone: ChipTone.ok),
          const SizedBox(height: IbhSpace.s8),
          Text(id, style: IbhText.mono.copyWith(fontSize: 11)),
          const SizedBox(height: IbhSpace.s12),
          OutlinedButton(
            onPressed: () async {
              final go = await showDialog<bool>(
                context: context,
                builder: (_) => AlertDialog(
                  title: const Text('Revoke this phone?'),
                  content: const Text('Use this if the phone is lost or replaced. Its signing key stops working at '
                      'once. Captures still waiting to upload will be rejected by the server. You can set the phone '
                      'up again with a new key.'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
                    FilledButton(
                        style: FilledButton.styleFrom(backgroundColor: IbhColors.badFg),
                        onPressed: () => Navigator.pop(context, true),
                        child: const Text('Revoke')),
                  ],
                ),
              );
              if (go != true) return;
              try {
                await s.revokeThisPhone();
                ref.invalidate(deviceProvider);
                if (context.mounted) {
                  ScaffoldMessenger.of(context)
                    ..hideCurrentSnackBar()
                    ..showSnackBar(const SnackBar(content: Text('This phone was revoked. Its signing key no longer works.')));
                }
              } catch (e) {
                if (context.mounted) showError(context, e);
              }
            },
            child: const Text('Revoke this phone'),
          ),
        ]),
      ),
      const Divider(height: IbhSpace.s32),
      const Text('Held by a licensed escrow partner, never by iBackHome.', style: IbhText.small),
      const SizedBox(height: IbhSpace.s24),
      OutlinedButton(
        onPressed: () => confirmSignOut(context, ref),
        child: const Text('Sign out'),
      ),
    ]);
  }
}
