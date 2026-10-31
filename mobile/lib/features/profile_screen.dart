import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'widgets.dart';

/// Your profile: what we hold about you (`GET /me`) and the one thing you can change here, your name
/// (`PATCH /me`). Phone and email are how you sign in. Time is always Nigerian time (WAT) for
/// supervisors and contractors, so there is no time-zone or country setting.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _name;
  bool _saving = false;
  String? _error;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    final me = ref.read(authProvider).me ?? const {};
    _name = TextEditingController(text: me['full_name'] as String? ?? '');
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
      _saved = false;
    });
    try {
      await ref.read(authProvider.notifier).updateProfile(fullName: _name.text.trim());
      if (mounted) setState(() => _saved = true);
    } catch (e) {
      if (mounted) setState(() => _error = ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final me = ref.watch(authProvider).me ?? const {};
    return Scaffold(
      appBar: const IbhAppBar(title: 'Your profile'),
      body: Form(
        key: _form,
        child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          if (_error != null) ...[
            Alert(_error!, tone: ChipTone.bad),
            const SizedBox(height: IbhSpace.s12),
          ],
          if (_saved) ...[
            const Alert('Saved. Your name is updated.', tone: ChipTone.ok),
            const SizedBox(height: IbhSpace.s12),
          ],
          const Text('Full name', style: _label),
          const SizedBox(height: IbhSpace.s8),
          TextFormField(
            controller: _name,
            textCapitalization: TextCapitalization.words,
            maxLength: 120,
            validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter your full name.' : null,
          ),
          const Text('Your client, the supervisor and our team see this name.', style: IbhText.small),
          const IbhSectionLabel('SIGN-IN AND ACCOUNT'),
          IbhGroup(children: [
            if (me['phone'] != null) _Row('Phone', '${me['phone']}'),
            if (me['email'] != null) _Row('Email', '${me['email']}'),
            _Row('Role', '${me['role']}'),
            _Row('Account status', me['status'] == 'suspended' ? 'Suspended' : 'Active'),
            const _Row('Time zone', 'Nigerian time (WAT), fixed'),
          ]),
          const SizedBox(height: IbhSpace.s8),
          Text('Your phone number or email is how you sign in, so it can\'t be changed here.', style: IbhText.small.copyWith(color: IbhColors.muted)),
        ]),
      ),
      bottomNavigationBar: BottomActionBar(children: [
        FilledButton(
          onPressed: _saving ? null : _save,
          child: _saving ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: IbhColors.white)) : const Text('Save'),
        ),
      ]),
    );
  }
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => IbhRow(
        title: label,
        titleStyle: IbhText.body.copyWith(color: IbhColors.muted),
        trailing: Flexible(child: Text(value, textAlign: TextAlign.right, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink))),
      );
}
