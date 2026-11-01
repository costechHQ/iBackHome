import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/ibh_tokens.dart';

/// The thin progress bar under the app bar of a step flow ("3 of 5"). Navy for the steps done.
class StepProgress extends StatelessWidget implements PreferredSizeWidget {
  const StepProgress({super.key, required this.step, required this.of});

  final int step;
  final int of;

  @override
  Size get preferredSize => const Size.fromHeight(4);

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Step $step of $of',
        child: SizedBox(
          height: 4,
          child: Row(children: [
            Expanded(flex: step, child: const ColoredBox(color: IbhColors.navy900, child: SizedBox.expand())),
            if (of > step) Expanded(flex: of - step, child: const ColoredBox(color: IbhColors.line, child: SizedBox.expand())),
          ]),
        ),
      );
}

/// A big, labelled radio card (the WhatsApp / SMS and Yes / No choices).
class RadioCard<T> extends StatelessWidget {
  const RadioCard({super.key, required this.value, required this.group, required this.label, required this.onChanged});

  final T value;
  final T group;
  final String label;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    final selected = value == group;
    return Semantics(
      inMutuallyExclusiveGroup: true,
      selected: selected,
      button: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(IbhRadius.control),
        onTap: () => onChanged(value),
        child: Container(
          constraints: const BoxConstraints(minHeight: 48),
          padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s16, vertical: IbhSpace.s12),
          decoration: BoxDecoration(
            color: IbhColors.white,
            borderRadius: BorderRadius.circular(IbhRadius.control),
            border: Border.all(color: selected ? IbhColors.navy900 : IbhColors.lineStrong, width: selected ? 2 : 1),
          ),
          child: Row(children: [
            Icon(selected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                size: 22, color: selected ? IbhColors.navy900 : IbhColors.muted),
            const SizedBox(width: IbhSpace.s12),
            Flexible(child: Text(label, style: IbhText.body.copyWith(fontWeight: FontWeight.w600, color: IbhColors.ink))),
          ]),
        ),
      ),
    );
  }
}

/// Six boxes for the one-time code. One real text field sits behind them, so paste, the number pad
/// and the phone's SMS autofill all work.
class OtpBoxes extends StatefulWidget {
  const OtpBoxes({super.key, required this.controller, this.onChanged, this.length = 6, this.enabled = true});

  final TextEditingController controller;
  final ValueChanged<String>? onChanged;
  final int length;
  final bool enabled;

  @override
  State<OtpBoxes> createState() => _OtpBoxesState();
}

class _OtpBoxesState extends State<OtpBoxes> {
  final _focus = FocusNode();

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_rebuild);
    _focus.addListener(_rebuild);
  }

  void _rebuild() => setState(() {});

  @override
  void dispose() {
    widget.controller.removeListener(_rebuild);
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final text = widget.controller.text;
    return Semantics(
      label: '6-digit code',
      textField: true,
      child: GestureDetector(
        onTap: () => _focus.requestFocus(),
        child: Stack(children: [
          Row(children: [
            for (var i = 0; i < widget.length; i++) ...[
              if (i > 0) const SizedBox(width: IbhSpace.s8),
              Expanded(
                child: Container(
                  height: 56,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: IbhColors.white,
                    borderRadius: BorderRadius.circular(IbhRadius.control),
                    border: Border.all(
                      color: _focus.hasFocus && i == text.length.clamp(0, widget.length - 1) ? IbhColors.accent : IbhColors.lineStrong,
                      width: _focus.hasFocus && i == text.length.clamp(0, widget.length - 1) ? 2 : 1,
                    ),
                  ),
                  child: Text(i < text.length ? text[i] : '', style: IbhText.h3.copyWith(fontSize: 22)),
                ),
              ),
            ],
          ]),
          // The real field: invisible, but it takes the focus, the keyboard and the pasted code.
          Positioned.fill(
            child: Opacity(
              opacity: 0,
              child: TextField(
                controller: widget.controller,
                focusNode: _focus,
                enabled: widget.enabled,
                autofocus: true,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                maxLength: widget.length,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                onChanged: widget.onChanged,
                decoration: const InputDecoration(counterText: ''),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}

/// The round icon badge that tops the onboarding pages.
class IconBadge extends StatelessWidget {
  const IconBadge(this.icon, {super.key, this.ok = false});

  final IconData icon;
  final bool ok;

  @override
  Widget build(BuildContext context) => Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(color: ok ? IbhColors.okBg : IbhColors.mist, shape: BoxShape.circle),
        child: Icon(icon, color: ok ? IbhColors.okFg : IbhColors.navy900),
      );
}

/// A row of equal buttons where one is selected (navy, white text): "Yes | Partly | No".
class ChoiceRow<T> extends StatelessWidget {
  const ChoiceRow({super.key, required this.options, required this.value, required this.onChanged});

  final Map<T, String> options;
  final T? value;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) => Row(children: [
        for (final e in options.entries) ...[
          if (e.key != options.keys.first) const SizedBox(width: IbhSpace.s8),
          Expanded(
            child: Semantics(
              button: true,
              selected: value == e.key,
              child: InkWell(
                borderRadius: BorderRadius.circular(IbhRadius.control),
                onTap: () => onChanged(e.key),
                child: Container(
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: value == e.key ? IbhColors.navy900 : IbhColors.white,
                    borderRadius: BorderRadius.circular(IbhRadius.control),
                    border: Border.all(color: value == e.key ? IbhColors.navy900 : IbhColors.lineStrong),
                  ),
                  child: Text(e.value, style: TextStyle(fontWeight: FontWeight.w700, color: value == e.key ? IbhColors.white : IbhColors.ink)),
                ),
              ),
            ),
          ),
        ],
      ]);
}

/// "− 7 +": a count with big buttons, kept between [min] and [max].
class CountStepper extends StatelessWidget {
  const CountStepper({super.key, required this.value, required this.onChanged, this.min = 0, this.max = 9999, this.label = 'count'});

  final int value;
  final ValueChanged<int> onChanged;
  final int min;
  final int max;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(color: IbhColors.mist, borderRadius: BorderRadius.circular(IbhRadius.control), border: Border.all(color: IbhColors.lineStrong)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          IconButton(
            tooltip: 'Decrease $label',
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            icon: const Icon(Icons.remove),
            onPressed: value > min ? () => onChanged(value - 1) : null,
          ),
          SizedBox(width: 56, child: Text('$value', textAlign: TextAlign.center, style: IbhText.h3)),
          IconButton(
            tooltip: 'Increase $label',
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            icon: const Icon(Icons.add),
            onPressed: value < max ? () => onChanged(value + 1) : null,
          ),
        ]),
      );
}
