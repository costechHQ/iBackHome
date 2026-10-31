import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/places.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'widgets.dart';

/// Your profile: what we hold about you (from `GET /me`) and the three fields you can change
/// (`PATCH /me`): name, country and time zone. Phone and email are how you sign in, so they are
/// shown but not edited here.
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _name;
  String? _country;
  late String _zone;
  bool _saving = false;
  String? _error;
  bool _saved = false;

  @override
  void initState() {
    super.initState();
    final me = ref.read(authProvider).me ?? const {};
    _name = TextEditingController(text: me['full_name'] as String? ?? '');
    _country = me['country'] as String?;
    _zone = me['timezone'] as String? ?? 'UTC';
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
      await ref
          .read(authProvider.notifier)
          .updateProfile(
            fullName: _name.text.trim(),
            country: _country,
            timezone: _zone,
          );
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
    final countries = withCurrent(profileCountries, _country);
    final zones = withCurrent(profileTimeZones, _zone);
    return Scaffold(
      appBar: AppBar(title: const Text('Your profile')),
      body: Form(
        key: _form,
        child: ListView(
          padding: const EdgeInsets.all(IbhSpace.s16),
          children: [
            if (_error != null) ...[
              Alert(_error!, tone: ChipTone.bad),
              const SizedBox(height: IbhSpace.s12),
            ],
            if (_saved) ...[
              const Alert(
                'Saved. Your details are updated.',
                tone: ChipTone.ok,
              ),
              const SizedBox(height: IbhSpace.s12),
            ],
            TextFormField(
              controller: _name,
              textCapitalization: TextCapitalization.words,
              maxLength: 120,
              decoration: const InputDecoration(labelText: 'Full name'),
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? 'Enter your full name.'
                  : null,
            ),
            const SizedBox(height: IbhSpace.s12),
            DropdownButtonFormField<String>(
              initialValue: _country,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Country'),
              items: [
                for (final e in countries.entries)
                  DropdownMenuItem(value: e.key, child: Text(e.value)),
              ],
              onChanged: (v) => setState(() => _country = v),
            ),
            const SizedBox(height: IbhSpace.s12),
            DropdownButtonFormField<String>(
              initialValue: _zone,
              isExpanded: true,
              decoration: const InputDecoration(labelText: 'Time zone'),
              items: [
                for (final e in zones.entries)
                  DropdownMenuItem(value: e.key, child: Text(e.value)),
              ],
              onChanged: (v) => setState(() => _zone = v ?? _zone),
            ),
            const SizedBox(height: IbhSpace.s16),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Save'),
            ),
            const Divider(height: IbhSpace.s32),
            const Text('Sign-in and account', style: IbhText.h3),
            const SizedBox(height: IbhSpace.s8),
            if (me['phone'] != null) _Row('Phone', '${me['phone']}'),
            if (me['email'] != null) _Row('Email', '${me['email']}'),
            _Row('Role', '${me['role']}'),
            _Row('Account status', '${me['status']}'),
            const SizedBox(height: IbhSpace.s8),
            const Text(
              'Your phone number or email is how you sign in, so it cannot be changed here.',
              style: IbhText.small,
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}
