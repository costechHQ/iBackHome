import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/sync_strip.dart';
import 'alerts_screen.dart';
import 'me_tab.dart';
import 'orders_screen.dart';
import 'projects_tab.dart';

import 'queue_screen.dart';
import 'spot_checks_screen.dart';

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
    // Supervisor: Projects, Spot checks, Sync, Me. Contractor: Projects, Orders, Alerts, Account (the
    // contractor's sync status is in Account; their captures upload by themselves).
    final tabs = supervisor
        ? <_Tab>[
            _Tab('Projects', Icons.home_outlined, Icons.home, name == null ? role : '$name · $role', const ProjectsTab(), strip: true),
            _Tab('Spot checks', Icons.fact_check_outlined, Icons.fact_check, 'Unannounced visits', const SpotChecksScreen()),
            _Tab('Sync', Icons.cloud_upload_outlined, Icons.cloud_upload, null, const QueueScreen(), strip: true, badge: _Badge.sync),
            _Tab('Me', Icons.person_outline, Icons.person, 'Supervisor account', const MeTab()),
          ]
        : <_Tab>[
            _Tab('Projects', Icons.home_outlined, Icons.home, name == null ? role : '$name · $role', const ProjectsTab(), strip: true),
            _Tab('Orders', Icons.inventory_2_outlined, Icons.inventory_2, 'Material orders', const OrdersTab()),
            _Tab('Alerts', Icons.notifications_outlined, Icons.notifications, null, const AlertsTab(), badge: _Badge.alerts),
            _Tab('Account', Icons.person_outline, Icons.person, 'Contractor account', const MeTab()),
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
                  icon: _withBadge(tab.badge, Icon(tab.icon)),
                  selectedIcon: _withBadge(tab.badge, Icon(tab.selectedIcon)),
                  label: tab.label,
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// The icon with its count: captures waiting (Sync) or unread alerts (Alerts).
Widget _withBadge(_Badge b, Icon icon) => switch (b) {
      _Badge.sync => _SyncBadge(icon),
      _Badge.alerts => _AlertsBadge(icon),
      _Badge.none => icon,
    };

/// Unread alerts on the Alerts tab (sample data until the feed route exists).
class _AlertsBadge extends ConsumerWidget {
  const _AlertsBadge(this.icon);
  final Icon icon;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unread = (ref.watch(alertsProvider).value ?? const []).where((a) => a['unread'] == true).length;
    return Badge(isLabelVisible: unread > 0, label: Text('$unread'), backgroundColor: IbhColors.navy900, child: icon);
  }
}

class _Tab {
  const _Tab(this.label, this.icon, this.selectedIcon, this.subtitle, this.body, {this.strip = false, this.badge = _Badge.none});
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final String? subtitle;
  final Widget body;
  final bool strip;
  final _Badge badge;
}

enum _Badge { none, sync, alerts }

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

