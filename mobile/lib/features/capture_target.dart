/// What the supervisor checks a milestone against comes from the server: ops' template for that kind of
/// milestone, copied into each milestone (`milestone['checklist']`, from `GET /projects/{id}/milestones`).
///
/// This generic list is only a fallback for a server that sends none (an older one). It is the same four
/// items the server falls back to, so the app and the server agree.
const defaultChecklist = <String>[
  'Work matches the bill of quantities',
  'Materials are as specified',
  'Workmanship is acceptable',
  'Site is safe and tidy',
];

/// The milestone's checklist as the server sent it, or the generic fallback if it sent none.
List<String> milestoneChecklist(Map<String, dynamic> milestone) {
  final items = (milestone['checklist'] as List?)?.map((e) => '$e').where((e) => e.trim().isNotEmpty).toList();
  return items == null || items.isEmpty ? defaultChecklist : items;
}

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
