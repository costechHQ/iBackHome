import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/sync_strip.dart';
import 'payout_screen.dart';
import 'permissions_screen.dart';
import 'profile_screen.dart';
import 'projects_tab.dart';

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
    final auth = ref.watch(authProvider);
    final supervisor = auth.isSupervisor;
    final name = auth.me?['full_name'] as String?;
    final role = supervisor ? 'supervisor' : 'contractor';
    // Supervisors also get spot checks; contractors do not do them. (Contractor tabs follow the
    // design, Projects / Orders / Alerts / Account, once those screens exist.)
    final tabs = <_Tab>[
      _Tab('Projects', Icons.home_outlined, Icons.home, name == null ? role : '$name · $role', const ProjectsTab(), strip: true),
      if (supervisor)
        _Tab('Spot checks', Icons.fact_check_outlined, Icons.fact_check, 'Unannounced visits', const SpotChecksScreen()),
      _Tab('Sync', Icons.cloud_upload_outlined, Icons.cloud_upload, null, const QueueScreen(), strip: true, badge: true),
      _Tab('Me', Icons.person_outline, Icons.person, supervisor ? 'Supervisor account' : 'Contractor account', const _MeTab()),
    ];
    final i = _tab.clamp(0, tabs.length - 1);
    final t = tabs[i];
    return Scaffold(
      appBar: IbhAppBar(title: t.label, subtitle: t.subtitle, leading: IbhBarLeading.logo),
      body: Column(children: [
        if (t.strip) const SyncStrip(),
        Expanded(child: t.body),
      ]),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: IbhColors.white,
          indicatorColor: IbhColors.accentTint,
          height: 72,
          labelTextStyle: WidgetStateProperty.resolveWith((s) => TextStyle(
                fontFamily: 'Inter',
                fontSize: 12,
                fontWeight: s.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
                color: s.contains(WidgetState.selected) ? IbhColors.navy900 : IbhColors.muted,
              )),
          iconTheme: WidgetStateProperty.resolveWith(
              (s) => IconThemeData(color: s.contains(WidgetState.selected) ? IbhColors.navy900 : IbhColors.muted)),
        ),
        child: DecoratedBox(
          decoration: const BoxDecoration(border: Border(top: BorderSide(color: IbhColors.line))),
          child: NavigationBar(
            selectedIndex: i,
            onDestinationSelected: (v) => setState(() => _tab = v),
            destinations: [
              for (final tab in tabs)
                NavigationDestination(
                  icon: tab.badge ? _SyncBadge(Icon(tab.icon)) : Icon(tab.icon),
                  selectedIcon: tab.badge ? _SyncBadge(Icon(tab.selectedIcon)) : Icon(tab.selectedIcon),
                  label: tab.label,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Tab {
  const _Tab(this.label, this.icon, this.selectedIcon, this.subtitle, this.body, {this.strip = false, this.badge = false});
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final String? subtitle;
  final Widget body;
  final bool strip;
  final bool badge;
}

/// The Sync tab's icon with the number of captures still waiting to upload.
class _SyncBadge extends ConsumerStatefulWidget {
  const _SyncBadge(this.icon);
  final Icon icon;

  @override
  ConsumerState<_SyncBadge> createState() => _SyncBadgeState();
}

class _SyncBadgeState extends ConsumerState<_SyncBadge> {
  late final Services _s = ref.read(servicesProvider);
  int _waiting = 0;

  @override
  void initState() {
    super.initState();
    _s.sync.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    _s.sync.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    final n = await _s.db.unsentCount();
    if (mounted) setState(() => _waiting = n);
  }

  @override
  Widget build(BuildContext context) => Badge(
        isLabelVisible: _waiting > 0,
        label: Text('$_waiting'),
        backgroundColor: IbhColors.navy900,
        child: widget.icon,
      );
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
      if (auth.isContractor) ...[
        const SizedBox(height: IbhSpace.s8),
        OutlinedButton(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const PayoutScreen())),
          child: const Text('Payout account'),
        ),
      ],
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
