import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// Why a list is empty and what fills it, with a button only when the person can act
/// (AND-SUPERVISOR-017, "Empty states").
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, required this.message, this.actionLabel, this.onAction});

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(IbhSpace.s32),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 56,
              height: 56,
              decoration: const BoxDecoration(color: IbhColors.mist, shape: BoxShape.circle),
              child: Icon(icon, color: IbhColors.navy900),
            ),
            const SizedBox(height: IbhSpace.s16),
            Text(title, textAlign: TextAlign.center, style: IbhText.h3.copyWith(fontSize: 18)),
            const SizedBox(height: IbhSpace.s8),
            Text(message, textAlign: TextAlign.center, style: IbhText.body),
            if (actionLabel != null) ...[
              const SizedBox(height: IbhSpace.s16),
              OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ]),
        ),
      );
}

/// Grey placeholder rows while a list loads (flat, no shimmer, light on low-end phones).
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.rows = 4});

  final int rows;

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Loading',
        child: ListView(
          physics: const NeverScrollableScrollPhysics(),
          padding: const EdgeInsets.all(IbhSpace.s16),
          children: [
            for (var i = 0; i < rows; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: IbhSpace.s12),
                child: Container(
                  height: 72,
                  decoration: BoxDecoration(
                    color: IbhColors.white,
                    borderRadius: BorderRadius.circular(IbhRadius.card),
                    border: Border.all(color: IbhColors.line),
                  ),
                  padding: const EdgeInsets.all(IbhSpace.s16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                    FractionallySizedBox(widthFactor: 0.6, child: _bar(14)),
                    const SizedBox(height: IbhSpace.s8),
                    FractionallySizedBox(widthFactor: 0.4, child: _bar(12)),
                  ]),
                ),
              ),
          ],
        ),
      );

  static Widget _bar(double h) =>
      Container(height: h, decoration: BoxDecoration(color: IbhColors.placeholder, borderRadius: BorderRadius.circular(IbhRadius.tag)));
}

/// The sticky bottom action area: one primary button, optionally a secondary under or beside it.
class BottomActionBar extends StatelessWidget {
  const BottomActionBar({super.key, required this.children, this.row = false});

  final List<Widget> children;

  /// Side by side (Retake | Save) instead of stacked.
  final bool row;

  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(color: IbhColors.white, border: Border(top: BorderSide(color: IbhColors.line))),
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(IbhSpace.s16),
            child: row
                ? Row(children: [
                    for (var i = 0; i < children.length; i++) ...[
                      if (i > 0) const SizedBox(width: IbhSpace.s12),
                      Expanded(child: children[i]),
                    ],
                  ])
                : Column(mainAxisSize: MainAxisSize.min, children: [
                    for (var i = 0; i < children.length; i++) ...[
                      if (i > 0) const SizedBox(height: IbhSpace.s8),
                      children[i],
                    ],
                  ]),
          ),
        ),
      );
}
