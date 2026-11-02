import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/push.dart';
import 'core/push_route.dart';
import 'core/services.dart';
import 'features/alerts_screen.dart';
import 'features/home_screen.dart';
import 'features/payout_screen.dart';
import 'features/vetting_screen.dart';
import 'features/sign_in_screen.dart';
import 'features/widgets.dart';
import 'ui/app_theme.dart';

class IbhApp extends ConsumerStatefulWidget {
  const IbhApp({super.key});

  @override
  ConsumerState<IbhApp> createState() => _IbhAppState();
}

class _IbhAppState extends ConsumerState<IbhApp> with WidgetsBindingObserver {
  final _navigator = GlobalKey<NavigatorState>();
  final _messenger = GlobalKey<ScaffoldMessengerState>();
  final List<StreamSubscription<PushMessage>> _pushSubs = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Push starts once a supervisor or contractor is fully signed in, and stops on sign-out (see signOut).
    ref.listenManual(authProvider, (_, a) {
      if (a.status == AuthStatus.signedIn && a.me != null && appRoles.contains(a.role) && a.me?['consent_required'] != true) {
        unawaited(ref.read(pushProvider).start());
      }
    }, fireImmediately: true);
    final push = ref.read(pushProvider);
    _pushSubs
      ..add(push.opened.listen((m) {
        final screen = screenForPush(m);
        if (screen != null) _navigator.currentState?.push(MaterialPageRoute<void>(builder: (_) => screen));
      }))
      ..add(push.arrived.listen((m) {
        ref.invalidate(alertsProvider);
        final text = m.body ?? m.title;
        if (text != null) {
          _messenger.currentState
            ?..hideCurrentSnackBar()
            ..showSnackBar(SnackBar(content: Text(text)));
        }
      }));
    Future.microtask(() async {
      await ref.read(authProvider.notifier).restore();
      final s = ref.read(servicesProvider);
      await s.db.promoteDrafts();
      s.sync.start();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    for (final s in _pushSubs) {
      s.cancel();
    }
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) ref.read(servicesProvider).sync.syncNow();
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);
    return MaterialApp(
      navigatorKey: _navigator,
      scaffoldMessengerKey: _messenger,
      title: 'iBackHome',
      debugShowCheckedModeBanner: false,
      theme: ibhAppTheme(),
      home: switch (auth.status) {
        AuthStatus.unknown => const Scaffold(body: Center(child: CircularProgressIndicator())),
        AuthStatus.signedOut => const SignInScreen(),
        AuthStatus.signedIn when auth.me != null && !appRoles.contains(auth.role) =>
          const WrongRoleScreen(),
        AuthStatus.signedIn when auth.me?['consent_required'] == true => const ConsentScreen(),
        AuthStatus.signedIn when auth.isSupervisor => const SupervisorOnboarding(),
        AuthStatus.signedIn when auth.isContractor => const _ContractorEntry(),
        AuthStatus.signedIn => const HomeScreen(),
      },
    );
  }
}

/// A contractor is asked for a payout account once, right after signing in. It can wait ("Later"),
/// and an offline start never blocks the app.
class _ContractorEntry extends ConsumerWidget {
  const _ContractorEntry();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (ref.watch(payoutSkippedProvider)) return const HomeScreen();
    return ref.watch(payoutProvider).when(
          loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
          error: (_, _) => const HomeScreen(),
          data: (saved) => saved == null ? const PayoutScreen(onboarding: true) : const HomeScreen(),
        );
  }
}
