import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/states.dart';
import 'widgets.dart';

/// The contractor's saved payout account; `null` until they save one (`GET /me/payout/recipient` is 404).
final payoutProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((ref) async {
  try {
    return await ref.read(servicesProvider).api.get<Map<String, dynamic>>('/me/payout/recipient');
  } on ApiError catch (e) {
    if (e.code == 'no_payout_recipient') return null;
    rethrow;
  }
});

final _banksProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final list = await ref.read(servicesProvider).api.get<List<dynamic>>('/banks');
  return list.cast<Map<String, dynamic>>();
});

/// True once the contractor chose "Later" on the payout step, until the app restarts.
class PayoutSkipped extends Notifier<bool> {
  @override
  bool build() => false;
  void skip() => state = true;
}

final payoutSkippedProvider = NotifierProvider<PayoutSkipped, bool>(PayoutSkipped.new);

/// AND-CONTRACTOR-001: "Where should we pay you?" The bank checks the account name; only the last four
/// digits are kept. Shown once after sign-in until an account is saved (it can wait), and from Account.
class PayoutScreen extends ConsumerStatefulWidget {
  const PayoutScreen({super.key, this.onboarding = false});

  /// First-time step: no back arrow, and a "Later" button.
  final bool onboarding;

  @override
  ConsumerState<PayoutScreen> createState() => _PayoutScreenState();
}

class _PayoutScreenState extends ConsumerState<PayoutScreen> {
  final _number = TextEditingController();
  String? _bank;
  String? _name; // found
  String? _problem; // not found / error
  bool _checking = false;
  bool _saving = false;

  @override
  void dispose() {
    _number.dispose();
    super.dispose();
  }

  bool get _complete => _bank != null && RegExp(r'^[0-9]{10}$').hasMatch(_number.text);

  Future<void> _check() async {
    if (!_complete) {
      setState(() {
        _name = null;
        _problem = null;
      });
      return;
    }
    setState(() {
      _checking = true;
      _name = null;
      _problem = null;
    });
    try {
      final r = await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/me/payout/recipient/resolve',
        body: {'bank_code': _bank, 'account_number': _number.text},
      );
      if (mounted) setState(() => _name = r['account_name'] as String?);
    } catch (e) {
      final err = ApiError.from(e);
      if (mounted) setState(() => _problem = err.isNetwork ? err.friendlyMessage : 'Check the 10-digit number and the bank.');
    } finally {
      if (mounted) setState(() => _checking = false);
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref.read(servicesProvider).api.put<Map<String, dynamic>>(
        '/me/payout/recipient',
        body: {'bank_code': _bank, 'account_number': _number.text},
      );
      ref.invalidate(payoutProvider);
      if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _problem = ApiError.from(e).friendlyMessage);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final banks = ref.watch(_banksProvider);
    final saved = ref.watch(payoutProvider).value;
    return Scaffold(
      backgroundColor: IbhColors.mist,
      appBar: IbhAppBar(title: 'Payout account', leading: widget.onboarding ? IbhBarLeading.none : IbhBarLeading.back),
      body: banks.when(
        loading: () => const SkeletonList(rows: 2),
        error: (e, _) => ErrorRetry(e, () => ref.invalidate(_banksProvider)),
        data: (list) => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          Text('Where should we pay you?', style: IbhText.h2.copyWith(fontSize: 26)),
          const SizedBox(height: IbhSpace.s16),
          if (saved != null && !widget.onboarding) ...[
            Alert('Saved: ${saved['account_name']} · ${saved['bank_name']} · ${saved['account_number_masked']}. Enter a new account below to change it.', tone: ChipTone.info),
            const SizedBox(height: IbhSpace.s16),
          ],
          const Text('Bank', style: _label),
          const SizedBox(height: IbhSpace.s8),
          DropdownButtonFormField<String>(
            initialValue: _bank,
            isExpanded: true,
            hint: const Text('Choose your bank'),
            items: [for (final b in list) DropdownMenuItem(value: b['code'] as String, child: Text(b['name'] as String, overflow: TextOverflow.ellipsis))],
            onChanged: (v) {
              setState(() => _bank = v);
              _check();
            },
          ),
          const SizedBox(height: IbhSpace.s16),
          const Text('Account number', style: _label),
          const SizedBox(height: IbhSpace.s8),
          TextField(
            controller: _number,
            keyboardType: TextInputType.number,
            maxLength: 10,
            decoration: InputDecoration(
              counterText: '',
              enabledBorder: _problem == null ? null : OutlineInputBorder(borderRadius: BorderRadius.circular(IbhRadius.control), borderSide: const BorderSide(color: IbhColors.badFg)),
            ),
            onChanged: (_) {
              setState(() {
                _name = null;
                _problem = null;
              });
              if (_complete) _check();
            },
          ),
          const SizedBox(height: IbhSpace.s16),
          if (_checking) const LinearProgressIndicator(),
          if (_name != null) _Result(ok: true, title: 'Account found', text: _name!),
          if (_problem != null) _Result(ok: false, title: 'We couldn\'t find that account', text: _problem!),
          const SizedBox(height: IbhSpace.s16),
          const Text('The bank checks the name. We keep only the last four digits of the number.', style: IbhText.small),
        ]),
      ),
      bottomNavigationBar: BottomActionBar(children: [
        FilledButton(
          onPressed: _name != null && !_saving ? _save : null,
          child: _saving ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: IbhColors.white)) : const Text('Save payout account'),
        ),
        if (widget.onboarding) TextButton(onPressed: () => ref.read(payoutSkippedProvider.notifier).skip(), child: const Text('Later')),
      ]),
    );
  }
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);

class _Result extends StatelessWidget {
  const _Result({required this.ok, required this.title, required this.text});
  final bool ok;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    final fg = ok ? IbhColors.okFg : IbhColors.badFg;
    return Container(
      padding: const EdgeInsets.all(IbhSpace.s16),
      decoration: BoxDecoration(color: ok ? IbhColors.okBg : IbhColors.badBg, borderRadius: BorderRadius.circular(IbhRadius.card)),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(ok ? Icons.check_circle_outline : Icons.cancel_outlined, color: fg, size: 22),
        const SizedBox(width: IbhSpace.s12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: fg)),
            Text(text, style: IbhText.body.copyWith(color: IbhColors.ink)),
          ]),
        ),
      ]),
    );
  }
}
