import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'widgets.dart';

/// AND-PUBLIC-001: phone or email, then the 6-digit code.
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key});

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _id = TextEditingController();
  final _code = TextEditingController();
  String _channel = 'sms';
  bool _codeSent = false;
  bool _busy = false;
  String? _error;

  bool get _isEmail => _id.text.contains('@');

  Future<void> _run(Future<void> Function() job) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await job();
    } catch (e) {
      final err = ApiError.from(e);
      setState(() => _error = err.friendlyMessage);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send() => _run(() async {
        final channel = _isEmail ? 'email' : _channel;
        await ref.read(authProvider.notifier).requestCode(_id.text.trim(), channel);
        setState(() => _codeSent = true);
      });

  Future<void> _verify() => _run(() => ref.read(authProvider.notifier).verify(_id.text.trim(), _code.text.trim()));

  @override
  Widget build(BuildContext context) => Scaffold(
        body: SafeArea(
          child: ListView(padding: const EdgeInsets.all(IbhSpace.s24), children: [
            const SizedBox(height: IbhSpace.s48),
            Image.asset('assets/images/ibackhome-logo-on-light.png', height: 44, alignment: Alignment.centerLeft, semanticLabel: 'iBackHome'),
            const SizedBox(height: IbhSpace.s8),
            const Text('Far from home, never out of sight.', style: IbhText.bodyLg),
            if (ref.watch(authProvider).sessionExpired) ...[
              const SizedBox(height: IbhSpace.s16),
              FutureBuilder<int>(
                future: ref.read(servicesProvider).db.unsentCount(),
                builder: (_, snap) => Alert(
                  'Your session ended. ${(snap.data ?? 0) > 0 ? 'Your ${snap.data} waiting capture${snap.data == 1 ? ' is' : 's are'} safe on this phone and will upload after you sign in.' : 'Sign in again to continue.'}',
                  tone: ChipTone.info,
                ),
              ),
            ],
            const SizedBox(height: IbhSpace.s40),
            TextField(
              controller: _id,
              enabled: !_codeSent,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Phone number or email'),
              onChanged: (_) => setState(() {}),
            ),
            if (!_codeSent && !_isEmail) ...[
              const SizedBox(height: IbhSpace.s12),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'sms', label: Text('Text message')),
                  ButtonSegment(value: 'whatsapp', label: Text('WhatsApp')),
                ],
                selected: {_channel},
                onSelectionChanged: (s) => setState(() => _channel = s.first),
              ),
            ],
            if (_codeSent) ...[
              const SizedBox(height: IbhSpace.s16),
              TextField(
                controller: _code,
                keyboardType: TextInputType.number,
                maxLength: 6,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(labelText: '6-digit code'),
                onChanged: (_) => setState(() {}),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: IbhSpace.s12),
              Alert(_error!, tone: ChipTone.bad),
            ],
            const SizedBox(height: IbhSpace.s24),
            FilledButton(
              onPressed: _busy || _id.text.trim().length < 3 || (_codeSent && _code.text.length != 6)
                  ? null
                  : (_codeSent ? _verify : _send),
              child: _busy
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_codeSent ? 'Sign in' : 'Send code'),
            ),
            if (_codeSent)
              TextButton(
                onPressed: _busy ? null : () => setState(() {
                      _codeSent = false;
                      _code.clear();
                    }),
                child: const Text('Use a different number or channel'),
              ),
          ]),
        ),
      );
}
