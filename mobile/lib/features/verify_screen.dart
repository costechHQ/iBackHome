import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'capture_target.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-008: verify a claimed milestone, or send it back with a reason.
///
/// A checklist item passes only with at least one photo from this phone, and a release still
/// needs the client's approval after this. With no signal the decision is queued and sent when
/// the photos have been accepted; the server checks the same rules again either way.
class VerifyScreen extends ConsumerStatefulWidget {
  const VerifyScreen({
    super.key,
    required this.projectId,
    required this.milestoneId,
    required this.milestoneName,
    this.projectTitle,
    this.sequence,
  });

  final String projectId;
  final String milestoneId;
  final String milestoneName;
  final String? projectTitle;
  final int? sequence;

  @override
  ConsumerState<VerifyScreen> createState() => _VerifyScreenState();
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> {
  final _notes = TextEditingController();
  List<QueuedCapture> _photos = const [];

  /// Checklist item text -> ids of this phone's captures that show it.
  final Map<String, Set<String>> _linked = {for (final i in defaultChecklist) i: <String>{}};
  bool _loaded = false;
  bool _busy = false;
  String? _conflict;

  @override
  void initState() {
    super.initState();
    ref.read(servicesProvider).db.all(projectId: widget.projectId).then((all) {
      if (!mounted) return;
      const usable = {CaptureStatus.queued, CaptureStatus.submitted, CaptureStatus.accepted};
      final photos = all.where((c) => usable.contains(c.status) && c.milestoneId == widget.milestoneId && !c.asContractor).toList();
      setState(() {
        _photos = photos;
        // Photos the supervisor linked to a checklist item at capture time start out ticked.
        for (final p in photos.where((p) => p.checklistItem != null)) {
          _linked.putIfAbsent(p.checklistItem!, () => <String>{}).add(p.id);
        }
        _loaded = true;
      });
    });
  }

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  int get _ready => _linked.values.where((s) => s.isNotEmpty).length;
  bool get _canVerify => _linked.isNotEmpty && _ready == _linked.length;

  Future<void> _verifyConfirm() async {
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Verify ${widget.milestoneName}?'),
        content: const Text('You are confirming every checklist item. The client is then asked to approve the release. A release needs both of you.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Verify')),
        ],
      ),
    );
    if (go == true) await _submit('verified');
  }

  Future<void> _sendBack() async {
    final reason = TextEditingController(text: _notes.text);
    final go = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: IbhColors.white,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(IbhRadius.sheet))),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => Padding(
          padding: EdgeInsets.fromLTRB(IbhSpace.s16, 0, IbhSpace.s16, IbhSpace.s16 + MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Send back ${widget.milestoneName}', style: IbhText.h3),
            const SizedBox(height: IbhSpace.s8),
            const Text('Say what needs fixing. The contractor and the client both see this.', style: IbhText.body),
            const SizedBox(height: IbhSpace.s12),
            TextField(controller: reason, maxLines: 4, autofocus: true, textCapitalization: TextCapitalization.sentences, onChanged: (_) => setSheet(() {})),
            const SizedBox(height: IbhSpace.s16),
            FilledButton(onPressed: reason.text.trim().isEmpty ? null : () => Navigator.pop(ctx, true), child: const Text('Send back to contractor')),
          ]),
        ),
      ),
    );
    final text = reason.text;
    reason.dispose();
    if (go != true) return;
    _notes.text = text;
    await _submit('rejected');
  }

  Future<void> _submit(String decision) async {
    setState(() {
      _busy = true;
      _conflict = null;
    });
    final s = ref.read(servicesProvider);
    final notes = _notes.text.trim().isEmpty ? null : _notes.text.trim();
    try {
      final byId = {for (final p in _photos) p.id: p};
      final entries = _linked.entries.where((e) => e.value.isNotEmpty).toList();
      final allAccepted = entries.every((e) => e.value.every((id) => byId[id]?.status == CaptureStatus.accepted));
      final path = '/milestones/${widget.milestoneId}/verify';
      final label = '${decision == 'verified' ? 'Verify' : 'Send back'} ${widget.milestoneName}';
      bool sent;
      if (decision == 'rejected') {
        sent = await s.sendOrQueue(kind: 'verify', path: path, body: {'decision': 'rejected', 'notes': notes, 'checklist': <Object>[]}, label: label, projectId: widget.projectId);
      } else if (allAccepted) {
        sent = await s.sendOrQueue(
          kind: 'verify',
          path: path,
          label: label,
          projectId: widget.projectId,
          body: {
            'decision': 'verified',
            'notes': notes,
            'checklist': [
              for (final e in entries) {'item': e.key, 'passed': true, 'evidence_ids': [for (final id in e.value) byId[id]!.evidenceId]}
            ],
          },
        );
      } else {
        // Some photos have not been accepted yet: keep the decision and send it when they are.
        await s.queueAction(
          kind: 'verify',
          path: path,
          label: label,
          projectId: widget.projectId,
          body: {
            'decision': 'verified',
            'notes': notes,
            'checklist': [
              for (final e in entries) {'item': e.key, 'passed': true, 'capture_ids': e.value.toList()}
            ],
          },
        );
        sent = false;
      }
      if (!mounted) return;
      if (!sent) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved on this phone. It will be sent when your photos are accepted and you have signal.')));
      }
      Navigator.of(context).pop(true);
    } on ApiError catch (e) {
      if (!mounted) return;
      if (e.status == 409) {
        // The milestone changed (for example it was already verified or is now disputed); nothing was done twice.
        setState(() => _conflict = e.message);
      } else {
        showError(context, e);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _pickPhotos(String item) => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        backgroundColor: IbhColors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(IbhRadius.sheet))),
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setSheet) => SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(IbhSpace.s16, 0, IbhSpace.s16, IbhSpace.s16),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(item, style: IbhText.h3.copyWith(fontSize: 18)),
                const SizedBox(height: IbhSpace.s4),
                Text('Tap the photos from this visit that show it.', style: IbhText.small.copyWith(color: IbhColors.muted)),
                const SizedBox(height: IbhSpace.s12),
                if (_photos.isEmpty)
                  const Text('No photos from this phone for this milestone yet. Capture on site first.', style: IbhText.body)
                else
                  Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
                    for (final c in _photos)
                      Semantics(
                        label: 'Photo taken ${watClock(c.capturedAt)}',
                        selected: _linked[item]!.contains(c.id),
                        child: GestureDetector(
                          onTap: () {
                            setState(() {
                              if (!_linked[item]!.remove(c.id)) _linked[item]!.add(c.id);
                            });
                            setSheet(() {});
                          },
                          child: Stack(children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(IbhRadius.control),
                              child: c.kind == 'video'
                                  ? const SizedBox(width: 80, height: 80, child: ColoredBox(color: IbhColors.camera, child: Icon(Icons.videocam, color: IbhColors.white)))
                                  : Image.file(File(c.filePath), width: 80, height: 80, fit: BoxFit.cover),
                            ),
                            if (_linked[item]!.contains(c.id)) const Positioned(right: 4, top: 4, child: Icon(Icons.check_circle, color: IbhColors.okFg)),
                            if (c.status != CaptureStatus.accepted) const Positioned(left: 4, bottom: 4, child: Icon(Icons.schedule, color: IbhColors.white, size: 18)),
                          ]),
                        ),
                      ),
                  ]),
                const SizedBox(height: IbhSpace.s16),
                FilledButton(onPressed: () => Navigator.pop(ctx), child: const Text('Done')),
              ]),
            ),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    if (_conflict != null) return _ConflictPage(name: widget.milestoneName, message: _conflict!, uploaded: _photos.length, project: widget.projectTitle);
    final subtitle = [if (widget.projectTitle != null) widget.projectTitle!, if (widget.sequence != null) 'claim ${widget.sequence}'].join(' · ');
    final total = _linked.length;
    return Scaffold(
      appBar: IbhAppBar(title: 'Verify ${widget.milestoneName}', subtitle: subtitle.isEmpty ? null : subtitle),
      body: !_loaded
          ? const SkeletonList(rows: 3)
          : ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
              Row(children: [
                Expanded(child: Text('$_ready of $total items have photos', style: IbhText.h3.copyWith(fontSize: 18))),
                _canVerify ? const StatusChip('Ready', tone: ChipTone.ok) : const StatusChip('Needs photos', tone: ChipTone.warn),
              ]),
              const SizedBox(height: IbhSpace.s12),
              if (_photos.isEmpty)
                const Padding(
                  padding: EdgeInsets.only(bottom: IbhSpace.s12),
                  child: Alert('No photos from this phone for this milestone yet. Capture on site, then verify.'),
                ),
              IbhGroup(children: [for (final e in _linked.entries) _row(e.key, e.value)]),
              const SizedBox(height: IbhSpace.s16),
              const Text('Your notes for the client', style: _label),
              const SizedBox(height: IbhSpace.s8),
              TextField(controller: _notes, maxLines: 3, textCapitalization: TextCapitalization.sentences),
              const SizedBox(height: IbhSpace.s12),
              Text('A release needs both your verification and the client\'s approval.', style: IbhText.small.copyWith(color: IbhColors.muted)),
            ]),
      bottomNavigationBar: BottomActionBar(children: [
        FilledButton(onPressed: _busy || !_canVerify ? null : _verifyConfirm, child: Text('Verify ${widget.milestoneName}')),
        OutlinedButton(onPressed: _busy ? null : _sendBack, child: const Text('Send back to contractor')),
      ]),
    );
  }

  Widget _row(String item, Set<String> ids) {
    final mine = _photos.where((p) => ids.contains(p.id)).toList();
    final accepted = mine.where((p) => p.status == CaptureStatus.accepted).length;
    final (chip, tone) = ids.isEmpty
        ? ('Needs a photo', ChipTone.warn)
        : (accepted == mine.length ? ('Accepted', ChipTone.ok) : ('Waiting', ChipTone.neutral));
    return IbhRow(
      onTap: () => _pickPhotos(item),
      leading: Icon(ids.isEmpty ? Icons.check_box_outline_blank : Icons.check_box, color: ids.isEmpty ? IbhColors.muted : IbhColors.navy900),
      title: item,
      subtitle: ids.isEmpty ? 'Tap to choose photos' : '${mine.length} photo${mine.length == 1 ? '' : 's'} · $accepted accepted',
      trailing: StatusChip(chip, tone: tone),
    );
  }
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);

/// The 409 page: the milestone changed, so the decision was not recorded and nothing was done twice.
/// The photos still upload.
class _ConflictPage extends StatelessWidget {
  const _ConflictPage({required this.name, required this.message, required this.uploaded, this.project});

  final String name;
  final String message;
  final int uploaded;
  final String? project;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: IbhAppBar(title: 'Not recorded', subtitle: project == null ? name : '$project · $name', leading: IbhBarLeading.close),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          Container(
            padding: const EdgeInsets.all(IbhSpace.s16),
            decoration: BoxDecoration(
              color: IbhColors.badBg,
              borderRadius: BorderRadius.circular(IbhRadius.control),
              border: const Border(left: BorderSide(color: IbhColors.badFg, width: 4)),
            ),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Icon(Icons.cancel_outlined, color: IbhColors.badFg),
              const SizedBox(width: IbhSpace.s12),
              Expanded(
                child: Text.rich(TextSpan(style: IbhText.body.copyWith(color: IbhColors.ink), children: [
                  TextSpan(text: '$name changed. ', style: const TextStyle(fontWeight: FontWeight.w700)),
                  const TextSpan(text: 'Your decision wasn\'t recorded.'),
                ])),
              ),
            ]),
          ),
          const SizedBox(height: IbhSpace.s12),
          IbhCard(child: Text(message, style: IbhText.body)),
          if (uploaded > 0) ...[
            const SizedBox(height: IbhSpace.s12),
            Container(
              padding: const EdgeInsets.all(IbhSpace.s16),
              decoration: BoxDecoration(color: IbhColors.okBg, borderRadius: BorderRadius.circular(IbhRadius.card)),
              child: Row(children: [
                const Icon(Icons.check_circle_outline, color: IbhColors.okFg),
                const SizedBox(width: IbhSpace.s12),
                Expanded(
                  child: Text.rich(TextSpan(style: IbhText.body.copyWith(color: IbhColors.ink), children: [
                    TextSpan(text: 'Your $uploaded capture${uploaded == 1 ? '' : 's'} still uploaded', style: const TextStyle(fontWeight: FontWeight.w700)),
                    const TextSpan(text: ' and are with iBackHome.'),
                  ])),
                ),
              ]),
            ),
          ],
          const SizedBox(height: IbhSpace.s16),
          Text('There\'s nothing to redo. iBackHome may ask you to visit again.', style: IbhText.body),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('OK')),
        ]),
      );
}
