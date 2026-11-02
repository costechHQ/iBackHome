import 'package:flutter/material.dart';

import '../features/milestone_screen.dart';
import '../features/project_screen.dart';
import '../features/reports_screen.dart';
import '../features/spot_checks_screen.dart';
import 'push.dart';

/// The screen a push is about, from the ids in its data (the server never sends names or amounts).
/// Null when it names nothing the app can open; the person then simply stays where they are.
Widget? screenForPush(PushMessage m) {
  final d = m.data;
  final project = d['project_id'];
  if (project != null && d['milestone_id'] != null) {
    return MilestoneScreen(projectId: project, milestoneId: d['milestone_id']!);
  }
  if (project != null && d['report_id'] != null) return ReportsScreen(projectId: project);
  if (d['spot_check_id'] != null) return const SpotChecksScreen();
  if (project != null) return ProjectScreen(projectId: project);
  return null;
}
