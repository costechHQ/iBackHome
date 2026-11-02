import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// A flat white card with a hairline border (no shadow). [emphasis] draws the 2dp navy outline the
/// design uses for "Today" and "Rotation" cards.
class IbhCard extends StatelessWidget {
  const IbhCard({super.key, required this.child, this.emphasis = false, this.padding = const EdgeInsets.all(IbhSpace.s16), this.onTap});

  final Widget child;
  final bool emphasis;
  final EdgeInsets padding;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(IbhRadius.card);
    return Material(
      color: IbhColors.white,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: BorderSide(color: emphasis ? IbhColors.navy900 : IbhColors.line, width: emphasis ? 2 : 1),
      ),
      child: InkWell(borderRadius: radius, onTap: onTap, child: Padding(padding: padding, child: child)),
    );
  }
}

/// A card holding rows separated by hairlines (the grouped lists in the design).
class IbhGroup extends StatelessWidget {
  const IbhGroup({super.key, required this.children, this.emphasis = false});

  final List<Widget> children;
  final bool emphasis;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(IbhRadius.card);
    return Material(
      color: IbhColors.white,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: radius,
        side: BorderSide(color: emphasis ? IbhColors.navy900 : IbhColors.line, width: emphasis ? 2 : 1),
      ),
      child: Column(children: [
        for (var i = 0; i < children.length; i++) ...[
          if (i > 0) const Divider(height: 1),
          children[i],
        ],
      ]),
    );
  }
}

/// One row of a group: a bold title, one or two lines under it, and something at the right.
/// At least 48dp tall; the whole row is the touch target when [onTap] is set.
class IbhRow extends StatelessWidget {
  const IbhRow({super.key, required this.title, this.subtitle, this.leading, this.trailing, this.onTap, this.titleStyle});

  final String title;
  final String? subtitle;
  final Widget? leading;
  final Widget? trailing;
  final VoidCallback? onTap;
  final TextStyle? titleStyle;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 48),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s16, vertical: IbhSpace.s12),
          child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
            if (leading != null) ...[leading!, const SizedBox(width: IbhSpace.s12)],
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: titleStyle ?? IbhText.body.copyWith(fontWeight: FontWeight.w600, color: IbhColors.ink)),
                if (subtitle != null) Text(subtitle!, style: IbhText.small.copyWith(color: IbhColors.muted)),
              ]),
            ),
            if (trailing != null) ...[const SizedBox(width: IbhSpace.s12), trailing!],
          ]),
        ),
      ),
    );
  }
}

/// A small section label above a group ("ASSIGNED", "DONE").
class IbhSectionLabel extends StatelessWidget {
  const IbhSectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(0, IbhSpace.s16, 0, IbhSpace.s8),
        child: Text(text, style: IbhText.caption.copyWith(color: IbhColors.muted)),
      );
}
