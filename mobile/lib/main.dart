import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'core/services.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final services = await Services.create();
  runApp(ProviderScope(
    overrides: [servicesProvider.overrideWithValue(services)],
    child: const IbhApp(),
  ));
}
