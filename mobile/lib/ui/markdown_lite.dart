import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// Shows the small part of Markdown the weekly report uses: `##` headings, `-` bullets, `**bold**`
/// and paragraphs. Anything else is shown as plain text. No links, images or HTML are ever drawn.
class MarkdownLite extends StatelessWidget {
  const MarkdownLite(this.source, {super.key});

  final String source;

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    for (final raw in source.split('\n')) {
      final line = raw.trimRight();
      if (line.trim().isEmpty) {
        children.add(const SizedBox(height: IbhSpace.s8));
      } else if (RegExp(r'^#{1,6}\s').hasMatch(line)) {
        children.add(Padding(
          padding: const EdgeInsets.only(top: IbhSpace.s8, bottom: IbhSpace.s4),
          child: Text(line.replaceFirst(RegExp(r'^#{1,6}\s+'), ''), style: IbhText.h3.copyWith(fontSize: 17)),
        ));
      } else if (RegExp(r'^\s*[-*]\s+').hasMatch(line)) {
        children.add(Padding(
          padding: const EdgeInsets.only(left: IbhSpace.s8, bottom: 2),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('•  ', style: IbhText.body),
            Expanded(child: _rich(line.replaceFirst(RegExp(r'^\s*[-*]\s+'), ''))),
          ]),
        ));
      } else {
        children.add(Padding(padding: const EdgeInsets.only(bottom: 2), child: _rich(line)));
      }
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: children);
  }

  /// `**bold**` spans, everything else plain.
  static Widget _rich(String text) {
    final spans = <InlineSpan>[];
    final parts = text.split('**');
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].isEmpty) continue;
      spans.add(TextSpan(text: parts[i], style: i.isOdd ? const TextStyle(fontWeight: FontWeight.w700, color: IbhColors.ink) : null));
    }
    return Text.rich(TextSpan(style: IbhText.body.copyWith(color: IbhColors.ink), children: spans));
  }
}
