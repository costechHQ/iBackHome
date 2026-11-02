import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/forms.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'home_screen.dart';
import 'permissions_screen.dart';
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

/// What a supervisor sees before they are approved: the application (AND-SUPERVISOR-001), then the
/// "approved" page and the phone set-up (AND-SUPERVISOR-002). They get the tabs only once ops have
/// marked every check passed (FR-02). An approval seen once is remembered, so a supervisor with no
/// signal can still open the app and the capture queue.
class SupervisorOnboarding extends ConsumerStatefulWidget {
  const SupervisorOnboarding({super.key});

  @override
  ConsumerState<SupervisorOnboarding> createState() => _SupervisorOnboardingState();
}

class _SupervisorOnboardingState extends ConsumerState<SupervisorOnboarding> {
  bool? _cachedApproved;
  bool? _phoneReady;

  @override
  void initState() {
    super.initState();
    _loadFlags();
  }

  Future<void> _loadFlags() async {
    final t = ref.read(servicesProvider).tokens;
    final a = await t.vettingApprovedCached();
    final d = await t.deviceEverRegistered();
    if (mounted) {
      setState(() {
        _cachedApproved = a;
        _phoneReady = d;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_cachedApproved == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final profile = ref.watch(vettingProvider);
    return profile.when(
      loading: () => _cachedApproved! ? const HomeScreen() : const Scaffold(body: SkeletonList(rows: 3)),
      error: (e, _) => _cachedApproved!
          ? const HomeScreen()
          : _Frame(
              title: 'Your application',
              signOut: true,
              child: ErrorRetry(e, () => ref.invalidate(vettingProvider)),
            ),
      data: (p) {
        if (p == null) return const ApplicationFlow();
        final status = p['vetting_status'];
        if (status == 'approved') {
          ref.read(servicesProvider).tokens.cacheVettingApproved(true);
          if (_phoneReady == true) return const HomeScreen();
          return _ApprovedPage(onDone: _loadFlags);
        }
        if (status == 'rejected') return _RejectedPage(profile: p);
        return _PendingPage(profile: p);
      },
    );
  }
}

/// A full-screen page with the design's app bar and a sticky bottom area.
class _Frame extends StatelessWidget {
  const _Frame({required this.title, required this.child, this.actions = const [], this.signOut = false});

  final String title;
  final Widget child;
  final List<Widget> actions;
  final bool signOut;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: IbhColors.mist,
        appBar: IbhAppBar(title: title, leading: IbhBarLeading.none),
        body: child,
        bottomNavigationBar: actions.isEmpty && !signOut
            ? null
            : BottomActionBar(children: [
                ...actions,
                if (signOut) Consumer(builder: (c, ref, _) => TextButton(onPressed: () => confirmSignOut(c, ref), child: const Text('Sign out'))),
              ]),
      );
}

class _PendingPage extends ConsumerWidget {
  const _PendingPage({required this.profile});
  final Map<String, dynamic> profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    Widget row(String title, String subtitle, bool done, String doneWord, String waitWord) => IbhRow(
          title: title,
          subtitle: subtitle,
          leading: Icon(done ? Icons.check_circle : Icons.schedule, color: done ? IbhColors.navy900 : IbhColors.muted),
          trailing: Text(done ? doneWord : waitWord,
              style: TextStyle(fontWeight: FontWeight.w700, color: done ? IbhColors.okFg : IbhColors.warnFg)),
        );
    return _Frame(
      title: 'Your application',
      signOut: true,
      actions: [
        OutlinedButton(
          style: OutlinedButton.styleFrom(backgroundColor: IbhColors.mist),
          onPressed: () => ref.invalidate(vettingProvider),
          child: const Text('Refresh status'),
        ),
      ],
      child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const Align(alignment: Alignment.centerLeft, child: StatusChip('Under review', tone: ChipTone.warn)),
        const SizedBox(height: IbhSpace.s12),
        Text('We\'re checking your details', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('Operations check your registration, your NIN and your two guarantors. You can be assigned to a project once every check has passed.',
            style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s16),
        IbhGroup(children: [
          row('Registration', '${profile['registration_body']} · ${profile['registration_no']}', profile['registration_verified'] == true, 'Verified', 'Checking'),
          row('NIN', 'Identity', profile['nin_verified'] == true, 'Verified', 'Checking'),
          row('Guarantor 1', 'Called by our team', profile['guarantor_1_verified'] == true, 'Confirmed', 'Calling'),
          row('Guarantor 2', 'Called by our team', profile['guarantor_2_verified'] == true, 'Confirmed', 'Calling'),
        ]),
      ]),
    );
  }
}

class _RejectedPage extends ConsumerWidget {
  const _RejectedPage({required this.profile});
  final Map<String, dynamic> profile;

  @override
  Widget build(BuildContext context, WidgetRef ref) => _Frame(
        title: 'Your application',
        signOut: true,
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => ApplicationFlow(
                    startAtForm: true,
                    registrationBody: profile['registration_body'] as String?,
                    registrationNo: profile['registration_no'] as String?))),
            child: const Text('Fix and re-apply'),
          ),
        ],
        child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          const Align(alignment: Alignment.centerLeft, child: StatusChip('Not approved', tone: ChipTone.bad)),
          const SizedBox(height: IbhSpace.s12),
          Text('We couldn\'t approve this yet', style: IbhText.h2.copyWith(fontSize: 26)),
          const SizedBox(height: IbhSpace.s16),
          Container(
            padding: const EdgeInsets.all(IbhSpace.s16),
            decoration: BoxDecoration(
              color: IbhColors.white,
              borderRadius: BorderRadius.circular(IbhRadius.card),
              border: Border.all(color: IbhColors.badBg, width: 2),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Reason from our team', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.badFg)),
              const SizedBox(height: IbhSpace.s8),
              Text('${profile['rejection_reason'] ?? 'No reason was given.'}', style: IbhText.body.copyWith(color: IbhColors.ink)),
              if (profile['vetted_at'] != null) ...[
                const SizedBox(height: IbhSpace.s8),
                Text(watDayTime(DateTime.parse(profile['vetted_at'] as String)),
                    style: IbhText.small.copyWith(color: IbhColors.muted)),
              ],
            ]),
          ),
          const SizedBox(height: IbhSpace.s16),
          const Text('Check the details and send your application again.', style: IbhText.body),
        ]),
      );
}

class _ApprovedPage extends ConsumerWidget {
  const _ApprovedPage({required this.onDone});
  final Future<void> Function() onDone;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final first = (ref.watch(authProvider).me?['full_name'] as String?)?.split(' ').first;
    return _Frame(
      title: 'Your application',
      signOut: true,
      actions: [
        FilledButton(
          onPressed: () async {
            await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const PermissionsScreen()));
            await onDone();
          },
          child: const Text('Set up this phone'),
        ),
      ],
      child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.check_circle_outline, ok: true)),
        const SizedBox(height: IbhSpace.s12),
        const Align(alignment: Alignment.centerLeft, child: StatusChip('Approved', tone: ChipTone.ok)),
        const SizedBox(height: IbhSpace.s12),
        Text(first == null || first.isEmpty ? 'You\'re approved' : 'You\'re approved, $first', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('Two quick things before your first site: allow the camera and location, then set up your capture key.',
            style: IbhText.bodyLg),
      ]),
    );
  }
}

const _registrationBodies = ['COREN', 'NIOB'];
const _guarantorRelations = ['Former employer', 'Colleague', 'Client', 'Family friend', 'Other'];
const _relativeRelations = ['Brother', 'Sister', 'Parent', 'Cousin', 'In-law', 'Other'];

class _Guarantor {
  final name = TextEditingController();
  final phone = TextEditingController();
  String? relation;

  bool get valid => name.text.trim().length >= 2 && phone.text.replaceAll(RegExp(r'[^0-9]'), '').length >= 7 && relation != null;

  /// "Ngozi Eze, +2348031234567, Former employer": the one text field the application API has.
  String get asText => '${name.text.trim()}, ${phone.text.trim()}, $relation';

  void dispose() {
    name.dispose();
    phone.dispose();
  }
}

class _Relative {
  _Relative(this.phone, this.relationship);
  final String phone;
  final String relationship;
}

/// AND-SUPERVISOR-001: Start, then five steps, then submit. The NIN step explains the check but
/// collects nothing: the application route has no NIN field, and operations verify it.
class ApplicationFlow extends ConsumerStatefulWidget {
  const ApplicationFlow({super.key, this.startAtForm = false, this.registrationBody, this.registrationNo});

  /// A re-application goes straight to the form, with the registration the server already has.
  final bool startAtForm;
  final String? registrationBody;
  final String? registrationNo;

  @override
  ConsumerState<ApplicationFlow> createState() => _ApplicationFlowState();
}

class _ApplicationFlowState extends ConsumerState<ApplicationFlow> {
  /// 0 = start, 1 registration, 2 NIN, 3 guarantors, 4 relatives, 5 review.
  late int _step = widget.startAtForm ? 1 : 0;
  late String _body = _registrationBodies.contains(widget.registrationBody) ? widget.registrationBody! : 'COREN';
  late final _number = TextEditingController(text: widget.registrationNo ?? '');
  final _g = [_Guarantor(), _Guarantor()];
  bool? _hasRelatives; // null until answered
  final List<_Relative> _relatives = [];
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _number.dispose();
    for (final g in _g) {
      g.dispose();
    }
    super.dispose();
  }

  bool get _step1ok => _number.text.trim().length >= 2;
  bool get _step3ok => _g.every((g) => g.valid);
  bool get _step4ok => _hasRelatives == false || (_hasRelatives == true && _relatives.isNotEmpty);

  void _go(int s) => setState(() {
        _step = s;
        _error = null;
      });

  void _back() {
    if (_step > 1) {
      _go(_step - 1);
    } else if (_step == 1 && !widget.startAtForm) {
      _go(0);
    }
  }

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
          'guarantor_1': _g[0].asText,
          'guarantor_2': _g[1].asText,
          'related_contractors': [
            if (_hasRelatives == true)
              for (final r in _relatives) {'contractor_phone': r.phone, 'relationship': r.relationship}
          ],
        },
      );
      ref.invalidate(vettingProvider);
      if (mounted && Navigator.of(context).canPop()) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) setState(() => _error = ApiError.from(e).friendlyMessage);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_step == 0) return _start();
    final (title, body, next, label) = switch (_step) {
      1 => ('Application', _registration(), _step1ok, 'Continue'),
      2 => ('Application', _nin(), true, 'Continue'),
      3 => ('Application', _guarantors(), _step3ok, 'Continue'),
      4 => ('Application', _relativesStep(), _step4ok, 'Continue'),
      _ => ('Application', _review(), !_busy, 'Submit application'),
    };
    return PopScope(
      canPop: _step == 0 || (_step == 1 && widget.startAtForm),
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
      backgroundColor: IbhColors.mist,
      appBar: IbhAppBar(title: title, trailingText: '$_step of 5'),
      body: Column(children: [
        StepProgress(step: _step, of: 5),
        Expanded(child: body),
      ]),
      bottomNavigationBar: BottomActionBar(children: [
        FilledButton(
          onPressed: next ? (_step == 5 ? _submit : () => _go(_step + 1)) : null,
          child: _busy ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: IbhColors.white)) : Text(label),
        ),
      ]),
    ));
  }

  Widget _start() => Scaffold(
        backgroundColor: IbhColors.mist,
        appBar: const IbhAppBar(title: 'Become a supervisor', leading: IbhBarLeading.none),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.person_outline)),
          const SizedBox(height: IbhSpace.s16),
          Text('Apply to supervise sites across Nigeria', style: IbhText.h2.copyWith(fontSize: 26)),
          const SizedBox(height: IbhSpace.s12),
          const Text('Five short steps. Have these ready:', style: IbhText.bodyLg),
          const SizedBox(height: IbhSpace.s16),
          const IbhGroup(children: [
            _ReadyRow('Professional registration', 'COREN or NIOB number'),
            _ReadyRow('Your NIN', '11 digits'),
            _ReadyRow('Two guarantors', 'Names and phone numbers'),
            _ReadyRow('Any relatives who are contractors', 'Their phone numbers'),
          ]),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: () => _go(1), child: const Text('Start')),
          Consumer(builder: (c, ref, _) => TextButton(onPressed: () => confirmSignOut(c, ref), child: const Text('Sign out'))),
        ]),
      );

  Widget _registration() => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Text('Your professional registration', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('We check it with the registering body.', style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s16),
        const Text('Registered with', style: _label),
        const SizedBox(height: IbhSpace.s8),
        Row(children: [
          for (var i = 0; i < _registrationBodies.length; i++) ...[
            if (i > 0) const SizedBox(width: IbhSpace.s12),
            Expanded(
              child: RadioCard<String>(value: _registrationBodies[i], group: _body, label: _registrationBodies[i], onChanged: (v) => setState(() => _body = v)),
            ),
          ],
        ]),
        const SizedBox(height: IbhSpace.s16),
        const Text('Registration number', style: _label),
        const SizedBox(height: IbhSpace.s8),
        TextField(controller: _number, textCapitalization: TextCapitalization.characters, onChanged: (_) => setState(() {})),
        if (_error != null) ...[const SizedBox(height: IbhSpace.s12), Alert(_error!, tone: ChipTone.bad)],
      ]);

  Widget _nin() => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Text('Your NIN', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('Our team checks your National Identification Number as part of vetting.', style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s16),
        const IbhCard(
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.lock_outline, size: 20),
            SizedBox(width: IbhSpace.s12),
            Expanded(
              child: Text('The app doesn\'t collect your NIN. After the check, only its last four digits are kept.', style: IbhText.body),
            ),
          ]),
        ),
      ]);

  Widget _guarantors() => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Text('Two guarantors', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('People who know your work. We\'ll call them.', style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s16),
        for (var i = 0; i < 2; i++) ...[
          IbhCard(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Guarantor ${i + 1}', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
              const SizedBox(height: IbhSpace.s12),
              TextField(
                controller: _g[i].name,
                textCapitalization: TextCapitalization.words,
                decoration: InputDecoration(hintText: 'Full name', semanticCounterText: 'Guarantor ${i + 1} name'),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: IbhSpace.s12),
              TextField(
                controller: _g[i].phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(hintText: 'Phone number'),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: IbhSpace.s12),
              DropdownButtonFormField<String>(
                initialValue: _g[i].relation,
                isExpanded: true,
                hint: const Text('Relationship to you'),
                items: [for (final r in _guarantorRelations) DropdownMenuItem(value: r, child: Text(r))],
                onChanged: (v) => setState(() => _g[i].relation = v),
              ),
            ]),
          ),
          const SizedBox(height: IbhSpace.s12),
        ],
      ]);

  Widget _relativesStep() => ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Text('Are any contractors in your family?', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s8),
        const Text('Brothers, cousins, in-laws: anyone who could be the contractor on a site.', style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s16),
        Row(children: [
          Expanded(child: RadioCard<bool?>(value: true, group: _hasRelatives, label: 'Yes', onChanged: (v) => setState(() => _hasRelatives = v))),
          const SizedBox(width: IbhSpace.s12),
          Expanded(child: RadioCard<bool?>(value: false, group: _hasRelatives, label: 'No', onChanged: (v) => setState(() => _hasRelatives = v))),
        ]),
        if (_hasRelatives == true) ...[
          const SizedBox(height: IbhSpace.s16),
          for (var i = 0; i < _relatives.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: IbhSpace.s8),
              child: IbhCard(
                padding: const EdgeInsets.all(IbhSpace.s12),
                child: Row(children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(_maskPhone(_relatives[i].phone), style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
                      Text('${_relatives[i].relationship} · contractor', style: IbhText.small.copyWith(color: IbhColors.muted)),
                    ]),
                  ),
                  IconButton(
                    tooltip: 'Remove this relative',
                    constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
                    icon: const Icon(Icons.close),
                    onPressed: () => setState(() => _relatives.removeAt(i)),
                  ),
                ]),
              ),
            ),
          if (_relatives.length < 20)
            InkWell(
              borderRadius: BorderRadius.circular(IbhRadius.card),
              onTap: _addRelative,
              child: Container(
                height: 52,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(IbhRadius.card),
                  border: Border.all(color: IbhColors.placeholderBorder),
                ),
                child: Text(_relatives.isEmpty ? '+ Add a relative' : '+ Add another relative', style: const TextStyle(fontWeight: FontWeight.w700, color: IbhColors.ink)),
              ),
            ),
        ],
        const SizedBox(height: IbhSpace.s16),
        const Text('You\'ll never be assigned to, or spot-check, their projects. Not declaring a relative can end your account.', style: IbhText.small),
      ]);

  static String _maskPhone(String p) {
    final d = p.replaceAll(RegExp(r'[^0-9+]'), '');
    return d.length <= 7 ? p : '${d.substring(0, d.length - 7)} ••• ${d.substring(d.length - 4)}';
  }

  Future<void> _addRelative() async {
    final phone = TextEditingController();
    String? relation;
    final added = await showModalBottomSheet<_Relative>(
      context: context,
      isScrollControlled: true,
      backgroundColor: IbhColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(IbhRadius.sheet))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => Padding(
          padding: EdgeInsets.fromLTRB(IbhSpace.s16, IbhSpace.s16, IbhSpace.s16, IbhSpace.s16 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Add a relative', style: IbhText.h3),
            const SizedBox(height: IbhSpace.s12),
            TextField(
              controller: phone,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(hintText: 'Their phone number'),
              onChanged: (_) => setSheet(() {}),
            ),
            const SizedBox(height: IbhSpace.s12),
            DropdownButtonFormField<String>(
              initialValue: relation,
              isExpanded: true,
              hint: const Text('How are they related to you?'),
              items: [for (final r in _relativeRelations) DropdownMenuItem(value: r, child: Text(r))],
              onChanged: (v) => setSheet(() => relation = v),
            ),
            const SizedBox(height: IbhSpace.s16),
            FilledButton(
              onPressed: phone.text.replaceAll(RegExp(r'[^0-9]'), '').length >= 7 && relation != null
                  ? () => Navigator.pop(ctx, _Relative(phone.text.trim(), relation!))
                  : null,
              child: const Text('Add'),
            ),
          ]),
        ),
      ),
    );
    phone.dispose();
    if (added != null) setState(() => _relatives.add(added));
  }

  Widget _review() {
    Widget row(String title, String subtitle, int step) => IbhRow(
          title: title,
          subtitle: subtitle,
          leading: const Icon(Icons.check_circle, color: IbhColors.navy900),
          trailing: TextButton(
            style: TextButton.styleFrom(minimumSize: const Size(48, 48)),
            onPressed: () => _go(step),
            child: Text('Edit', semanticsLabel: 'Edit $title', style: const TextStyle(fontWeight: FontWeight.w700, color: IbhColors.okFg)),
          ),
        );
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      Text('Check and submit', style: IbhText.h2.copyWith(fontSize: 26)),
      const SizedBox(height: IbhSpace.s8),
      const Text('Tap any item to change it.', style: IbhText.bodyLg),
      const SizedBox(height: IbhSpace.s16),
      IbhGroup(children: [
        row('$_body · ${_number.text.trim()}', 'Professional registration', 1),
        row('NIN', 'Checked by our team', 2),
        row('${_g[0].name.text.trim()} · ${_g[1].name.text.trim()}', 'Guarantors', 3),
        row(_hasRelatives == true ? '${_relatives.length} relative${_relatives.length == 1 ? '' : 's'} declared' : 'No relatives declared',
            _hasRelatives == true ? _relatives.map((r) => '${_maskPhone(r.phone)} · ${r.relationship}').join(', ') : 'Contractors in your family', 4),
      ]),
      if (_error != null) ...[const SizedBox(height: IbhSpace.s12), Alert(_error!, tone: ChipTone.bad)],
    ]);
  }
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);

class _ReadyRow extends StatelessWidget {
  const _ReadyRow(this.title, this.subtitle);
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => IbhRow(
        title: title,
        subtitle: subtitle,
        leading: const Icon(Icons.radio_button_unchecked, color: IbhColors.muted),
      );
}
