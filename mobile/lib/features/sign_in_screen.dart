import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/dial_codes.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/forms.dart';
import '../ui/states.dart';
import 'widgets.dart';

/// AND-PUBLIC-001: phone or email, then the 6-digit code. Also the "Sign in again to upload" page
/// (AND-SUPERVISOR-003) when the server ended the session and captures are waiting.
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

enum _Tab { phone, email }

/// A code works for 5 minutes (server rule); the design lets people ask for another after 30 s.
const _codeLife = Duration(minutes: 5);
const _resendAfter = Duration(seconds: 30);

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _phone = TextEditingController();
  final _email = TextEditingController();
  final _code = TextEditingController();
  _Tab _tab = _Tab.phone;
  DialCode _country = dialCodes.first;
  String _channel = 'whatsapp';
  bool _codeSent = false;
  bool _busy = false;
  String? _error;
  late bool _expiredPage = ref.read(authProvider).sessionExpired;

  Timer? _ticker;
  DateTime? _sentAt;
  Duration _now = Duration.zero;

  @override
  void dispose() {
    _ticker?.cancel();
    _phone.dispose();
    _email.dispose();
    _code.dispose();
    super.dispose();
  }

  /// What the server gets as `identifier`.
  String get _identifier => _tab == _Tab.email ? _email.text.trim() : composePhone(_country, _phone.text);

  String get _sentChannel => _tab == _Tab.email ? 'email' : _channel;

  bool get _canSend => _tab == _Tab.email ? _email.text.trim().contains('@') : _phone.text.replaceAll(RegExp(r'[^0-9]'), '').length >= 6;

  Duration get _sinceSent => _sentAt == null ? Duration.zero : _now;

  Duration get _expiresIn => _codeLife - _sinceSent;

  Duration get _resendIn => _resendAfter - _sinceSent;

  void _startClock() {
    _ticker?.cancel();
    _sentAt = DateTime.now();
    _now = Duration.zero;
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() => _now = DateTime.now().difference(_sentAt!));
    });
  }

  Future<void> _run(Future<void> Function() job) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await job();
    } catch (e) {
      final err = ApiError.from(e);
      if (mounted) setState(() => _error = err.friendlyMessage);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send({String? channel}) => _run(() async {
        if (channel != null) _channel = channel;
        await ref.read(authProvider.notifier).requestCode(_identifier, _sentChannel);
        _code.clear();
        _startClock();
        if (mounted) setState(() => _codeSent = true);
      });

  Future<void> _verify() => _run(() => ref.read(authProvider.notifier).verify(_identifier, _code.text.trim()));

  void _back() => setState(() {
        _codeSent = false;
        _code.clear();
        _error = null;
        _ticker?.cancel();
      });

  String _clock(Duration d) {
    final s = d.isNegative ? 0 : d.inSeconds;
    return '${s ~/ 60}:${(s % 60).toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    if (_expiredPage) return _SessionExpired(onSignIn: () => setState(() => _expiredPage = false));
    return Scaffold(
      backgroundColor: IbhColors.white,
      appBar: const _LogoBar(),
      body: SafeArea(child: _codeSent ? _codeStep() : _identifierStep()),
    );
  }

  Widget _identifierStep() => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const SizedBox(height: IbhSpace.s8),
        Text('Sign in or create an account', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('We\'ll send you a 6-digit code. There are no passwords.', style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s24),
        _Tabs(tab: _tab, onChanged: (t) => setState(() {
              _tab = t;
              _error = null;
            })),
        const SizedBox(height: IbhSpace.s16),
        if (_tab == _Tab.phone) ...[
          const Text('Phone number', style: _label),
          const SizedBox(height: IbhSpace.s8),
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(
              width: 112,
              child: DropdownButtonFormField<DialCode>(
                initialValue: _country,
                isExpanded: true,
                decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 14)),
                selectedItemBuilder: (_) => [for (final c in dialCodes) Text(c.short, style: const TextStyle(fontWeight: FontWeight.w600))],
                items: [for (final c in dialCodes) DropdownMenuItem(value: c, child: Text('${c.name} +${c.dial}'))],
                onChanged: (c) => setState(() => _country = c ?? _country),
              ),
            ),
            const SizedBox(width: IbhSpace.s8),
            Expanded(
              child: TextField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                autofillHints: const [AutofillHints.telephoneNumber],
                decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 14)),
                onChanged: (_) => setState(() {}),
              ),
            ),
          ]),
          const SizedBox(height: IbhSpace.s16),
          const Text('Send the code by', style: _label),
          const SizedBox(height: IbhSpace.s8),
          Row(children: [
            Expanded(child: RadioCard<String>(value: 'whatsapp', group: _channel, label: 'WhatsApp', onChanged: (v) => setState(() => _channel = v))),
            const SizedBox(width: IbhSpace.s12),
            Expanded(child: RadioCard<String>(value: 'sms', group: _channel, label: 'SMS', onChanged: (v) => setState(() => _channel = v))),
          ]),
        ] else ...[
          const Text('Email address', style: _label),
          const SizedBox(height: IbhSpace.s8),
          TextField(
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            onChanged: (_) => setState(() {}),
          ),
        ],
        if (_error != null) ...[
          const SizedBox(height: IbhSpace.s12),
          Alert(_error!, tone: ChipTone.bad),
        ],
        const SizedBox(height: IbhSpace.s24),
        FilledButton(
          onPressed: _busy || !_canSend ? null : _send,
          child: _busy ? const _Spinner() : const Text('Send code'),
        ),
        const SizedBox(height: IbhSpace.s16),
        const Text('Invited to a project? Use the phone number or email your invitation was sent to.', style: IbhText.small),
      ]);

  Widget _codeStep() {
    final expired = _expiresIn <= Duration.zero;
    final canResend = _resendIn <= Duration.zero;
    final viaEmail = _tab == _Tab.email;
    final otherChannel = _channel == 'whatsapp' ? 'sms' : 'whatsapp';
    final via = switch (_sentChannel) { 'whatsapp' => 'WhatsApp', 'sms' => 'SMS', _ => 'email' };
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      TextButton.icon(
        style: TextButton.styleFrom(alignment: Alignment.centerLeft, minimumSize: const Size(48, 48), padding: EdgeInsets.zero),
        onPressed: _busy ? null : _back,
        icon: const Icon(Icons.arrow_back_ios_new, size: 14),
        label: const Text('Back', style: TextStyle(fontWeight: FontWeight.w600)),
      ),
      Text('Enter your code', style: IbhText.h2.copyWith(fontSize: 26)),
      const SizedBox(height: IbhSpace.s8),
      Text.rich(
        TextSpan(style: IbhText.bodyLg, children: [
          TextSpan(text: 'We sent a 6-digit code by $via to '),
          TextSpan(text: maskIdentifier(_identifier), style: const TextStyle(fontWeight: FontWeight.w700, color: IbhColors.ink)),
          const TextSpan(text: '. '),
          WidgetSpan(
            alignment: PlaceholderAlignment.baseline,
            baseline: TextBaseline.alphabetic,
            child: InkWell(
              onTap: _back,
              child: const Text('Change', style: TextStyle(color: IbhColors.accent, decoration: TextDecoration.underline, fontSize: 16)),
            ),
          ),
        ]),
      ),
      const SizedBox(height: IbhSpace.s24),
      OtpBoxes(controller: _code, enabled: !_busy, onChanged: (_) => setState(() {})),
      const SizedBox(height: IbhSpace.s16),
      Row(children: [
        Icon(Icons.schedule, size: 18, color: expired ? IbhColors.badFg : IbhColors.muted),
        const SizedBox(width: IbhSpace.s8),
        Text(expired ? 'This code has expired. Ask for a new one.' : 'Code expires in ${_clock(_expiresIn)}',
            style: IbhText.small.copyWith(color: expired ? IbhColors.badFg : IbhColors.muted)),
      ]),
      if (_error != null) ...[
        const SizedBox(height: IbhSpace.s12),
        Alert(_error!, tone: ChipTone.bad),
      ],
      const SizedBox(height: IbhSpace.s16),
      FilledButton(
        onPressed: _busy || _code.text.length != 6 || expired ? null : _verify,
        child: _busy ? const _Spinner() : const Text('Verify'),
      ),
      const Divider(height: IbhSpace.s32),
      const Text('Didn\'t get it?', style: IbhText.small),
      const SizedBox(height: IbhSpace.s8),
      Wrap(spacing: IbhSpace.s16, runSpacing: 0, crossAxisAlignment: WrapCrossAlignment.center, children: [
        if (canResend)
          _LinkButton('Resend code', _busy ? null : () => _send())
        else
          Text('Resend in ${_clock(_resendIn)}', style: IbhText.small.copyWith(fontWeight: FontWeight.w700, color: IbhColors.muted)),
        if (!viaEmail) _LinkButton(otherChannel == 'sms' ? 'Send by SMS' : 'Send by WhatsApp', _busy ? null : () => _send(channel: otherChannel)),
        _LinkButton(viaEmail ? 'Use phone instead' : 'Use email instead', _busy
            ? null
            : () => setState(() {
                  _tab = viaEmail ? _Tab.phone : _Tab.email;
                  _back();
                })),
      ]),
    ]);
  }
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);

class _Spinner extends StatelessWidget {
  const _Spinner();
  @override
  Widget build(BuildContext context) =>
      const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: IbhColors.white));
}

class _LinkButton extends StatelessWidget {
  const _LinkButton(this.text, this.onTap);
  final String text;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => TextButton(
        style: TextButton.styleFrom(minimumSize: const Size(48, 48), padding: const EdgeInsets.symmetric(horizontal: 4), foregroundColor: IbhColors.accent),
        onPressed: onTap,
        child: Text(text, style: const TextStyle(decoration: TextDecoration.underline, fontWeight: FontWeight.w600)),
      );
}

/// Phone | Email, as a two-segment control.
class _Tabs extends StatelessWidget {
  const _Tabs({required this.tab, required this.onChanged});
  final _Tab tab;
  final ValueChanged<_Tab> onChanged;

  @override
  Widget build(BuildContext context) {
    Widget seg(_Tab t, String label) {
      final on = tab == t;
      return Expanded(
        child: Semantics(
          button: true,
          selected: on,
          child: InkWell(
            borderRadius: BorderRadius.circular(IbhRadius.control),
            onTap: () => onChanged(t),
            child: Container(
              height: 44,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: on ? IbhColors.white : Colors.transparent,
                borderRadius: BorderRadius.circular(IbhRadius.control),
                border: on ? Border.all(color: IbhColors.frame) : null,
              ),
              child: Text(label, style: TextStyle(fontWeight: FontWeight.w700, color: on ? IbhColors.ink : IbhColors.muted)),
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(color: IbhColors.mist, borderRadius: BorderRadius.circular(IbhRadius.card)),
      child: Row(children: [seg(_Tab.phone, 'Phone'), seg(_Tab.email, 'Email')]),
    );
  }
}

/// The wordmark bar at the top of the signed-out screens.
class _LogoBar extends StatelessWidget implements PreferredSizeWidget {
  const _LogoBar();

  @override
  Size get preferredSize => const Size.fromHeight(57);

  @override
  Widget build(BuildContext context) => Material(
        color: IbhColors.white,
        child: SafeArea(
          bottom: false,
          child: Container(
            height: 56,
            alignment: Alignment.centerLeft,
            padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s16),
            decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: IbhColors.line))),
            child: Image.asset('assets/images/ibackhome-logo-on-light.png', height: 32, semanticLabel: 'iBackHome'),
          ),
        ),
      );
}

/// "Sign in again to upload": shown when the server ended the session. The queue is safe.
class _SessionExpired extends ConsumerWidget {
  const _SessionExpired({required this.onSignIn});
  final VoidCallback onSignIn;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        backgroundColor: IbhColors.white,
        body: SafeArea(
          child: Column(children: [
            Expanded(
              child: ListView(padding: const EdgeInsets.all(IbhSpace.s24), children: [
                const SizedBox(height: IbhSpace.s24),
                const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.lock_outline)),
                const SizedBox(height: IbhSpace.s16),
                Text('Sign in again to upload', style: IbhText.h2.copyWith(fontSize: 26)),
                const SizedBox(height: IbhSpace.s12),
                const Text('Your session ended. Your captures are safe on this phone and keep their original time and place.',
                    style: IbhText.bodyLg),
                const SizedBox(height: IbhSpace.s16),
                FutureBuilder<int>(
                  future: ref.read(servicesProvider).db.unsentCount(),
                  builder: (_, snap) {
                    final n = snap.data ?? 0;
                    if (n == 0) return const SizedBox.shrink();
                    return Container(
                      padding: const EdgeInsets.all(IbhSpace.s16),
                      decoration: BoxDecoration(color: IbhColors.neutralBg, borderRadius: BorderRadius.circular(IbhRadius.card)),
                      child: Row(children: [
                        const StatusChip('Queued', tone: ChipTone.neutral),
                        const SizedBox(width: IbhSpace.s12),
                        Expanded(
                          child: Text.rich(TextSpan(style: IbhText.body, children: [
                            TextSpan(text: '$n capture${n == 1 ? '' : 's'}', style: const TextStyle(fontWeight: FontWeight.w700, color: IbhColors.ink)),
                            const TextSpan(text: ' waiting to upload'),
                          ])),
                        ),
                      ]),
                    );
                  },
                ),
                const SizedBox(height: IbhSpace.s16),
                Text('Sign in within 72 hours of taking them, or they can\'t be accepted.', style: IbhText.small.copyWith(color: IbhColors.muted)),
              ]),
            ),
            BottomActionBar(children: [FilledButton(onPressed: onSignIn, child: const Text('Sign in'))]),
          ]),
        ),
      );
}
