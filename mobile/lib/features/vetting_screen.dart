import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'widgets.dart';

/// The supervisor's own vetting profile; `null` when they have not applied yet.
final vettingProvider = FutureProvider.autoDispose<Map<String, dynamic>?>((ref) async {
  try {
    return await ref.read(servicesProvider).api.get<Map<String, dynamic>>('/supervisors/me/profile');
  } on ApiError catch (e) {
    if (e.code == 'supervisor_profile_not_found') return null;
    rethrow;
  }
});

/// Shows [child] once the supervisor is approved; before that, the application or its status.
/// A supervisor cannot be assigned to a project until ops mark every check passed (FR-02).
class VettingGate extends ConsumerWidget {
  const VettingGate({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (!ref.watch(authProvider).isSupervisor) return child;
    final profile = ref.watch(vettingProvider);
    return profile.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorRetry(e, () => ref.invalidate(vettingProvider)),
      data: (p) {
        if (p == null) return const ApplicationForm();
        if (p['vetting_status'] == 'approved') return child;
        return VettingStatus(profile: p);
      },
    );
  }
}

/// AND-SUPERVISOR-001: pending (with the four checks), rejected (with the reason, and a way to apply again).
class VettingStatus extends ConsumerWidget {
  const VettingStatus({super.key, required this.profile});
  final Map<String, dynamic> profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rejected = profile['vetting_status'] == 'rejected';
    Widget check(String label, bool done) => ListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          leading: Icon(done ? Icons.check_circle : Icons.schedule, color: done ? IbhColors.okFg : IbhColors.muted),
          title: Text(label),
        );
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      Text(rejected ? 'Your application was not approved' : 'Your application is being checked', style: IbhText.h3),
      const SizedBox(height: IbhSpace.s8),
      StatusChip(rejected ? 'Rejected' : 'Pending', tone: rejected ? ChipTone.bad : ChipTone.warn),
      const SizedBox(height: IbhSpace.s16),
      if (rejected)
        Alert('${profile['rejection_reason'] ?? 'No reason was given.'}', tone: ChipTone.bad)
      else
        const Text('Operations check your registration, your NIN and two guarantors. You can be assigned to a '
            'project once every check has passed.'),
      const SizedBox(height: IbhSpace.s12),
      check('Professional registration (${profile['registration_body']} ${profile['registration_no']})',
          profile['registration_verified'] == true),
      check('NIN', profile['nin_verified'] == true),
      check('Guarantor 1', profile['guarantor_1_verified'] == true),
      check('Guarantor 2', profile['guarantor_2_verified'] == true),
      const SizedBox(height: IbhSpace.s16),
      if (rejected)
        FilledButton(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => Scaffold(appBar: AppBar(title: const Text('Apply again')), body: const ApplicationForm()))),
          child: const Text('Apply again'),
        )
      else
        OutlinedButton(onPressed: () => ref.invalidate(vettingProvider), child: const Text('Check again')),
    ]);
  }
}

class ApplicationForm extends ConsumerStatefulWidget {
  const ApplicationForm({super.key});

  @override
  ConsumerState<ApplicationForm> createState() => _ApplicationFormState();
}

class _Relation {
  final phone = TextEditingController();
  final relationship = TextEditingController();
}

class _ApplicationFormState extends ConsumerState<ApplicationForm> {
  String _body = 'COREN';
  final _number = TextEditingController();
  final _g1 = TextEditingController();
  final _g2 = TextEditingController();
  final List<_Relation> _relations = [];
  bool _busy = false;
  String? _error;

  bool get _valid =>
      _number.text.trim().length >= 2 && _g1.text.trim().length >= 5 && _g2.text.trim().length >= 5;

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(servicesProvider).api.put<Map<String, dynamic>>(
        '/supervisors/me/profile',
        body: {
          'registration_body': _body,
          'registration_no': _number.text.trim(),
          'guarantor_1': _g1.text.trim(),
          'guarantor_2': _g2.text.trim(),
          'related_contractors': [
            for (final r in _relations)
              if (r.phone.text.trim().isNotEmpty)
                {'contractor_phone': r.phone.text.trim(), 'relationship': r.relationship.text.trim()}
          ],
        },
      );
      ref.invalidate(vettingProvider);
      if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
    } catch (e) {
      setState(() => _error = ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const Text('Apply to supervise', style: IbhText.h3),
        const SizedBox(height: IbhSpace.s8),
        const Text('Operations check your registration, your NIN and two guarantors before you can be assigned.'),
        const SizedBox(height: IbhSpace.s16),
        DropdownButtonFormField<String>(
          initialValue: _body,
          decoration: const InputDecoration(labelText: 'Registered with'),
          items: const [
            DropdownMenuItem(value: 'COREN', child: Text('COREN (engineers)')),
            DropdownMenuItem(value: 'NIOB', child: Text('NIOB (builders)')),
            DropdownMenuItem(value: 'ARCON', child: Text('ARCON (architects)')),
          ],
          onChanged: (v) => setState(() => _body = v ?? 'COREN'),
        ),
        const SizedBox(height: IbhSpace.s12),
        TextField(
            controller: _number,
            decoration: const InputDecoration(labelText: 'Registration number'),
            onChanged: (_) => setState(() {})),
        const SizedBox(height: IbhSpace.s12),
        TextField(
            controller: _g1,
            decoration: const InputDecoration(labelText: 'Guarantor 1', helperText: 'Name and phone, e.g. Ngozi Eze, 08031234567'),
            onChanged: (_) => setState(() {})),
        const SizedBox(height: IbhSpace.s12),
        TextField(
            controller: _g2,
            decoration: const InputDecoration(labelText: 'Guarantor 2', helperText: 'Name and phone'),
            onChanged: (_) => setState(() {})),
        const SizedBox(height: IbhSpace.s16),
        const Text('Contractors you are related to', style: TextStyle(fontWeight: FontWeight.w600)),
        const Text('You will never be assigned to, or spot-check, a contractor you list here.', style: IbhText.small),
        for (final r in _relations)
          Padding(
            padding: const EdgeInsets.only(top: IbhSpace.s8),
            child: Row(children: [
              Expanded(child: TextField(controller: r.phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Contractor phone'))),
              const SizedBox(width: IbhSpace.s8),
              Expanded(child: TextField(controller: r.relationship, decoration: const InputDecoration(labelText: 'Relationship'))),
            ]),
          ),
        TextButton.icon(
            onPressed: _relations.length >= 20 ? null : () => setState(() => _relations.add(_Relation())),
            icon: const Icon(Icons.add),
            label: const Text('Add a related contractor')),
        if (_error != null) ...[const SizedBox(height: IbhSpace.s8), Alert(_error!, tone: ChipTone.bad)],
        const SizedBox(height: IbhSpace.s16),
        FilledButton(onPressed: _busy || !_valid ? null : _submit, child: const Text('Submit application')),
      ]);
}
