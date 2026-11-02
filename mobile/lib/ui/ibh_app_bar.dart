import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// The design's app bar: a title with an optional subtitle line, and either the logo mark (top-level
/// tabs), a back arrow, or a close cross. 56dp tall, flat, with a hairline under it.
enum IbhBarLeading { logo, back, close, none }

class IbhAppBar extends StatelessWidget implements PreferredSizeWidget {
  const IbhAppBar({
    super.key,
    required this.title,
    this.subtitle,
    this.leading = IbhBarLeading.back,
    this.actions = const [],
    this.trailingText,
  });

  final String title;
  final String? subtitle;
  final IbhBarLeading leading;
  final List<Widget> actions;

  /// A small grey note at the right, e.g. "1 of 2" in a step flow.
  final String? trailingText;

  @override
  Size get preferredSize => const Size.fromHeight(57);

  @override
  Widget build(BuildContext context) {
    final lead = switch (leading) {
      IbhBarLeading.logo => Padding(
          padding: const EdgeInsets.only(left: IbhSpace.s16, right: IbhSpace.s12),
          child: Image.asset('assets/images/ibackhome-mark-on-light.png', height: 32, width: 32, semanticLabel: 'iBackHome'),
        ),
      IbhBarLeading.back => IconButton(
          tooltip: 'Back',
          icon: const Icon(Icons.arrow_back_ios_new, size: 20),
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          onPressed: () => Navigator.maybePop(context),
        ),
      IbhBarLeading.close => IconButton(
          tooltip: 'Close',
          icon: const Icon(Icons.close),
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          onPressed: () => Navigator.maybePop(context),
        ),
      IbhBarLeading.none => const SizedBox(width: IbhSpace.s16),
    };
    return Material(
      color: IbhColors.white,
      child: SafeArea(
        bottom: false,
        child: Container(
          height: 56,
          decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: IbhColors.line))),
          child: Row(children: [
            lead,
            Expanded(
              child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: IbhText.h3.copyWith(fontSize: 18, height: 1.33)),
                if (subtitle != null)
                  Text(subtitle!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: IbhText.small.copyWith(fontSize: 13, color: IbhColors.muted, height: 1.2)),
              ]),
            ),
            if (trailingText != null)
              Padding(
                padding: const EdgeInsets.only(right: IbhSpace.s16),
                child: Text(trailingText!, style: IbhText.small.copyWith(fontWeight: FontWeight.w600, color: IbhColors.muted)),
              ),
            ...actions,
          ]),
        ),
      ),
    );
  }
}
