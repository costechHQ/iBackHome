import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-008: verify a claimed milestone, or send it back with a reason.
///
/// A checklist item passes only with at least one accepted photo from this phone. The server
/// checks the same rule again, so this screen never decides on its own.
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
  final Set<String> evidenceIds = {};
}

class _VerifyScreenState extends ConsumerState<VerifyScreen> {
  final _notes = TextEditingController();
  final List<_Item> _items = [_Item('Work matches the bill of quantities')];
  List<QueuedCapture> _photos = const [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    ref.read(servicesProvider).db.all(projectId: widget.projectId).then((all) {
      if (!mounted) return;
      final photos = all
          .where((c) =>
              c.status == CaptureStatus.accepted &&
              c.evidenceId != null &&
              c.milestoneId == widget.milestoneId &&
              !c.asContractor)
          .toList();
      setState(() {
        _photos = photos;
        // Photos the supervisor linked to a checklist item at capture start out ticked.
        final linked = <String, Set<String>>{};
        for (final p in photos.where((p) => p.checklistItem != null)) {
          linked.putIfAbsent(p.checklistItem!, () => {}).add(p.evidenceId!);
        }
        if (linked.isNotEmpty) {
          _items
            ..clear()
            ..addAll(linked.entries.map((e) => _Item(e.key)..evidenceIds.addAll(e.value)));
        }
      });
    });
  }

  bool get _canVerify =>
      _items.isNotEmpty && _items.every((i) => i.controller.text.trim().isNotEmpty && i.evidenceIds.isNotEmpty);

  Future<void> _submit(String decision) async {
    if (decision == 'rejected' && _notes.text.trim().isEmpty) {
      showError(context, 'Write the reason the contractor will see.');
      return;
    }
    setState(() => _busy = true);
    try {
      await ref.read(servicesProvider).api.post<Map<String, dynamic>>(
        '/milestones/${widget.milestoneId}/verify',
        body: {
          'decision': decision,
          'notes': _notes.text.trim().isEmpty ? null : _notes.text.trim(),
          'checklist': decision == 'verified'
              ? [
                  for (final i in _items)
                    {'item': i.controller.text.trim(), 'passed': true, 'evidence_ids': i.evidenceIds.toList()}
                ]
              : <Map<String, dynamic>>[],
        },
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text('Verify ${widget.milestoneName}')),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          if (_photos.isEmpty)
            const Alert('No accepted photos from this phone for this milestone yet. Capture on site, wait for '
                '"Accepted" in the queue, then verify.'),
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
                      GestureDetector(
                        onTap: () => setState(() {
                          if (!item.evidenceIds.remove(c.evidenceId)) item.evidenceIds.add(c.evidenceId!);
                        }),
                        child: Stack(children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(IbhRadius.control),
                            child: Image.file(File(c.filePath), width: 72, height: 72, fit: BoxFit.cover),
                          ),
                          if (item.evidenceIds.contains(c.evidenceId))
                            const Positioned(right: 4, top: 4, child: Icon(Icons.check_circle, color: IbhColors.okFg)),
                        ]),
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
