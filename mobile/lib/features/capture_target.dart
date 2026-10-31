/// Checklist items the supervisor checks a milestone against.
///
/// PLACEHOLDER: the design says these come from ops templates, and the API has no template
/// route yet, so every milestone uses this generic list. Replace when templates exist.
const defaultChecklist = <String>[
  'Work matches the bill of quantities',
  'Materials are as specified',
  'Workmanship is acceptable',
  'Site is safe and tidy',
];

/// What a capture belongs to: a milestone, a spot check, or a delivery.
class CaptureTarget {
  const CaptureTarget({
    required this.projectId,
    required this.title,
    this.subtitle,
    this.fixedItem,
    this.milestoneId,
    this.contextRef,
    this.fence,
    this.asContractor = false,
    this.checklist = defaultChecklist,
  });

  final String projectId;
  final String title;

  /// The line under the title in the app bar (the project name).
  final String? subtitle;

  /// A capture that always belongs to one checklist line (a delivery line), so the review step does not ask.
  final String? fixedItem;
  final String? milestoneId;

  /// e.g. `spot_check:<id>`; kept on the phone, so the right screen can find its photos.
  final String? contextRef;
  final List<List<double>>? fence;
  final bool asContractor;
  final List<String> checklist;
}
