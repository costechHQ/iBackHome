import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/services.dart';
import 'features/home_screen.dart';
import 'features/sign_in_screen.dart';
import 'features/widgets.dart';
import 'theme/ibh_tokens.dart';

class IbhApp extends ConsumerStatefulWidget {
  const IbhApp({super.key});

  @override
  ConsumerState<IbhApp> createState() => _IbhAppState();
}

class _IbhAppState extends ConsumerState<IbhApp> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
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
      title: 'iBackHome',
      debugShowCheckedModeBanner: false,
      theme: ibhTheme(),
      home: switch (auth.status) {
        AuthStatus.unknown => const Scaffold(body: Center(child: CircularProgressIndicator())),
        AuthStatus.signedOut => const SignInScreen(),
        AuthStatus.signedIn when auth.me != null && !appRoles.contains(auth.role) =>
          const WrongRoleScreen(),
        AuthStatus.signedIn when auth.me?['consent_required'] == true => const ConsentScreen(),
        AuthStatus.signedIn => const HomeScreen(),
      },
    );
  }
}
