import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'capture_target.dart';

/// AND-SUPERVISOR-006, review step: link the photo to a checklist item, add a note, then save
/// it to the upload queue or retake. Nothing uploads until it is saved.
class ReviewScreen extends ConsumerStatefulWidget {
  const ReviewScreen({super.key, required this.capture, required this.target});

  final QueuedCapture capture;
  final CaptureTarget target;

  @override
  ConsumerState<ReviewScreen> createState() => _ReviewScreenState();
}

class _ReviewScreenState extends ConsumerState<ReviewScreen> {
  final _note = TextEditingController();
  String? _item;

  Future<void> _save() async {
    await ref.read(servicesProvider).db.save(widget.capture.id, note: _note.text, checklistItem: _item);
    if (mounted) Navigator.of(context).pop(true);
  }

  Future<void> _retake() async {
    await ref.read(servicesProvider).db.discard(widget.capture);
    if (mounted) Navigator.of(context).pop(false);
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.capture;
    final showChecklist = !widget.target.asContractor && widget.target.milestoneId != null;
    return PopScope(
      // Going back keeps the capture as a draft; it is promoted to the queue on the next launch.
      child: Scaffold(
        appBar: AppBar(title: const Text('Review')),
        body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(IbhRadius.card),
            child: c.kind == 'video' ? Container(height: 220, color: IbhColors.camera, alignment: Alignment.center, child: const Icon(Icons.videocam, color: IbhColors.white, size: 56)) : Image.file(File(c.filePath), height: 320, fit: BoxFit.cover),
          ),
          const SizedBox(height: IbhSpace.s12),
          Text('${c.lat.toStringAsFixed(5)}, ${c.lon.toStringAsFixed(5)} · ±${c.accuracyM.round()} m · '
              '${c.capturedAt.toLocal().toString().substring(0, 16)}', style: IbhText.mono.copyWith(fontSize: 12)),
          const SizedBox(height: IbhSpace.s4),
          const Text('Signed on this phone. The server will check the site boundary, the signature and reuse.',
              style: IbhText.small),
          if (showChecklist) ...[
            const SizedBox(height: IbhSpace.s16),
            DropdownButtonFormField<String>(
              initialValue: _item,
              decoration: const InputDecoration(labelText: 'Checklist item this photo shows'),
              items: [for (final i in widget.target.checklist) DropdownMenuItem(value: i, child: Text(i, overflow: TextOverflow.ellipsis))],
              onChanged: (v) => setState(() => _item = v),
            ),
          ],
          const SizedBox(height: IbhSpace.s12),
          TextField(
            controller: _note,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Note (optional, stays on this phone)'),
          ),
          const SizedBox(height: IbhSpace.s24),
          FilledButton(onPressed: _save, child: const Text('Save')),
          const SizedBox(height: IbhSpace.s8),
          OutlinedButton(onPressed: _retake, child: const Text('Retake')),
        ]),
      ),
    );
  }
}
