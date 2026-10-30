import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'capture_target.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-008: verify a claimed milestone, or send it back with a reason.
///
/// A checklist item passes only with at least one photo from this phone, and a release still
/// needs the client's approval after this. With no signal the decision is queued and sent when
/// the photos have been accepted; the server checks the same rules again either way.
class VerifyScreen extends ConsumerStatefulWidget {
  const VerifyScreen({super.key, required this.projectId, required this.milestoneId, required this.milestoneName});

  final String projectId;
  final String milestoneId;
  final String milestoneName;

  @override
  ConsumerState<VerifyScreen> createState() => _VerifyScreenState();
}

class _Item {
  _Item(String text) : controller = TextEditingController(text: text);
  final TextEditingController controller;
  final Set<String> captureIds = {};
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> {
  final _notes = TextEditingController();
  final List<_Item> _items = [_Item(defaultChecklist.first)];
  List<QueuedCapture> _photos = const [];
  bool _busy = false;
  String? _conflict;

  @override
  void initState() {
    super.initState();
    ref.read(servicesProvider).db.all(projectId: widget.projectId).then((all) {
      if (!mounted) return;
      const usable = {CaptureStatus.queued, CaptureStatus.submitted, CaptureStatus.accepted};
      final photos = all
          .where((c) => usable.contains(c.status) && c.milestoneId == widget.milestoneId && !c.asContractor)
          .toList();
      setState(() {
        _photos = photos;
        // Photos the supervisor linked to a checklist item at capture start out ticked.
        final linked = <String, Set<String>>{};
        for (final p in photos.where((p) => p.checklistItem != null)) {
          linked.putIfAbsent(p.checklistItem!, () => {}).add(p.id);
        }
        if (linked.isNotEmpty) {
          _items
            ..clear()
            ..addAll(linked.entries.map((e) => _Item(e.key)..captureIds.addAll(e.value)));
        }
      });
    });
  }

  bool get _canVerify =>
      _items.isNotEmpty && _items.every((i) => i.controller.text.trim().isNotEmpty && i.captureIds.isNotEmpty);

  Future<void> _submit(String decision) async {
    if (decision == 'rejected' && _notes.text.trim().isEmpty) {
      showError(context, 'Write the reason the contractor will see.');
      return;
    }
    setState(() {
      _busy = true;
      _conflict = null;
    });
    final s = ref.read(servicesProvider);
    final notes = _notes.text.trim().isEmpty ? null : _notes.text.trim();
    try {
      final byId = {for (final p in _photos) p.id: p};
      final allAccepted = _items.every((i) => i.captureIds.every((id) => byId[id]?.status == CaptureStatus.accepted));
      final path = '/milestones/${widget.milestoneId}/verify';
      final label = '${decision == 'verified' ? 'Verify' : 'Send back'} ${widget.milestoneName}';
      bool sent;
      if (decision == 'rejected') {
        sent = await s.sendOrQueue(
            kind: 'verify', path: path, body: {'decision': 'rejected', 'notes': notes, 'checklist': <Object>[]},
            label: label, projectId: widget.projectId);
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
              for (final i in _items)
                {
                  'item': i.controller.text.trim(),
                  'passed': true,
                  'evidence_ids': [for (final id in i.captureIds) byId[id]!.evidenceId],
                }
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
              for (final i in _items)
                {'item': i.controller.text.trim(), 'passed': true, 'capture_ids': i.captureIds.toList()}
            ],
          },
        );
        sent = false;
      }
      if (!mounted) return;
      if (!sent) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
            content: Text('Saved on this phone. It will be sent when your photos are accepted and you have signal.')));
      }
      Navigator.of(context).pop(true);
    } on ApiError catch (e) {
      if (!mounted) return;
      if (e.status == 409) {
        // The milestone changed (for example it was already verified); nothing was done twice.
        setState(() => _conflict = e.message);
      } else {
        showError(context, e);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Verify ${widget.milestoneName}')),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          if (_conflict != null) ...[
            Alert('This milestone changed, so your decision was not applied and nothing was done twice. $_conflict '
                'Go back and refresh the project.', tone: ChipTone.bad),
            const SizedBox(height: IbhSpace.s12),
          ],
          const Alert('A release needs both your verification and the client\'s approval.', tone: ChipTone.info),
          const SizedBox(height: IbhSpace.s12),
          if (_photos.isEmpty)
            const Alert('No photos from this phone for this milestone yet. Capture on site, then verify.'),
          for (final item in _items)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(IbhSpace.s12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  TextField(
                    controller: item.controller,
                    decoration: const InputDecoration(labelText: 'What you checked'),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: IbhSpace.s8),
                  Wrap(spacing: IbhSpace.s8, runSpacing: IbhSpace.s8, children: [
                    for (final c in _photos)
                      Semantics(
                        label: 'Photo taken ${c.capturedAt.toLocal().toString().substring(0, 16)}',
                        selected: item.captureIds.contains(c.id),
                        child: GestureDetector(
                          onTap: () => setState(() {
                            if (!item.captureIds.remove(c.id)) item.captureIds.add(c.id);
                          }),
                          child: Stack(children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(IbhRadius.control),
                              child: c.kind == 'video'
                                  ? const SizedBox(width: 72, height: 72, child: ColoredBox(color: IbhColors.camera, child: Icon(Icons.videocam, color: IbhColors.white)))
                                  : Image.file(File(c.filePath), width: 72, height: 72, fit: BoxFit.cover),
                            ),
                            if (item.captureIds.contains(c.id))
                              const Positioned(right: 4, top: 4, child: Icon(Icons.check_circle, color: IbhColors.okFg)),
                            if (c.status != CaptureStatus.accepted)
                              const Positioned(left: 4, bottom: 4, child: Icon(Icons.schedule, color: IbhColors.white, size: 18)),
                          ]),
                        ),
                      ),
                  ]),
                ]),
              ),
            ),
          TextButton.icon(
            icon: const Icon(Icons.add),
            label: const Text('Add checklist item'),
            onPressed: () => setState(() => _items.add(_Item(''))),
          ),
          const SizedBox(height: IbhSpace.s8),
          TextField(
            controller: _notes,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Notes (needed if you send it back)'),
          ),
          const SizedBox(height: IbhSpace.s24),
          FilledButton(
            onPressed: _busy || !_canVerify ? null : () => _submit('verified'),
            child: const Text('Verify milestone'),
          ),
          const SizedBox(height: IbhSpace.s8),
          OutlinedButton(
            onPressed: _busy ? null : () => _submit('rejected'),
            child: const Text('Send back with reason'),
          ),
        ]),
      );
}
