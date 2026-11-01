import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// The design's confirmation: a bottom sheet with a title, one or two sentences, a full-width primary
/// button and a quiet "keep" button under it (AND-SUPERVISOR-016, "Confirmation dialog" and
/// "Destructive dialog"). A destructive one has a red button and is used only for things that cannot
/// be undone (deleting a capture, revoking a phone). The safe choice is always one tap away.
///
/// Returns true only when the person chose the primary button.
Future<bool> confirmSheet(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
  String cancelLabel = 'Cancel',
  bool destructive = false,
  String? footnote,
}) async {
  final go = await showModalBottomSheet<bool>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    backgroundColor: IbhColors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(IbhRadius.sheet))),
    builder: (ctx) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(IbhSpace.s16, 0, IbhSpace.s16, IbhSpace.s16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: IbhText.h3),
          const SizedBox(height: IbhSpace.s8),
          Text(message, style: IbhText.body),
          const SizedBox(height: IbhSpace.s16),
          FilledButton(
            style: destructive ? FilledButton.styleFrom(backgroundColor: IbhColors.badFg) : null,
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(confirmLabel),
          ),
          const SizedBox(height: IbhSpace.s8),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: IbhColors.mist, foregroundColor: IbhColors.ink),
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(cancelLabel),
          ),
          if (footnote != null) ...[
            const SizedBox(height: IbhSpace.s12),
            Text(footnote, style: IbhText.small.copyWith(color: IbhColors.muted)),
          ],
        ]),
      ),
    ),
  );
  return go == true;
}
