import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/capture_rules.dart';
import '../core/geo.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'capture_target.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-006, "Check the photo": link it to a checklist item, add a note, then save it to
/// the upload queue or retake. Nothing uploads until it is saved.
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

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    await ref.read(servicesProvider).db.save(widget.capture.id, note: _note.text, checklistItem: _item ?? widget.target.fixedItem);
    if (mounted) Navigator.of(context).pop(true);
  }

  Future<void> _retake() async {
    await ref.read(servicesProvider).db.discard(widget.capture);
    if (mounted) Navigator.of(context).pop(false);
  }

  /// Inside the boundary (with the 25 m allowance), outside, or unknown (no boundary yet).
  ({String label, ChipTone tone})? get _where {
    final fence = widget.target.fence;
    if (fence == null) return null;
    final d = Geo.distanceToFence(fence, widget.capture.lat, widget.capture.lon);
    return d <= fenceAllowanceM ? (label: 'Inside site', tone: ChipTone.ok) : (label: '${d.round()} m outside', tone: ChipTone.warn);
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.capture;
    final showChecklist = !widget.target.asContractor && widget.target.milestoneId != null;
    final where = _where;
    return Scaffold(
      appBar: IbhAppBar(title: c.kind == 'video' ? 'Check the video' : 'Check the photo', subtitle: widget.target.title),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        Stack(children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(IbhRadius.card),
            child: c.kind == 'video'
                ? Container(height: 220, color: IbhColors.camera, alignment: Alignment.center, child: const Icon(Icons.videocam, color: IbhColors.white, size: 56))
                : Image.file(File(c.filePath), height: 300, width: double.infinity, fit: BoxFit.cover),
          ),
          if (where != null) Positioned(left: 12, top: 12, child: StatusChip(where.label, tone: where.tone)),
        ]),
        if (showChecklist) ...[
          const SizedBox(height: IbhSpace.s16),
          const Text('Checklist item', style: _label),
          const SizedBox(height: IbhSpace.s8),
          DropdownButtonFormField<String>(
            initialValue: _item,
            isExpanded: true,
            hint: const Text('Choose the item this shows'),
            items: [for (final i in widget.target.checklist) DropdownMenuItem(value: i, child: Text(i, overflow: TextOverflow.ellipsis))],
            onChanged: (v) => setState(() => _item = v),
          ),
        ],
        const SizedBox(height: IbhSpace.s16),
        Text.rich(TextSpan(style: _label, children: [
          const TextSpan(text: 'Notes '),
          TextSpan(text: '(optional, stay on this phone)', style: IbhText.small.copyWith(color: IbhColors.muted)),
        ])),
        const SizedBox(height: IbhSpace.s8),
        TextField(controller: _note, maxLines: 3, textCapitalization: TextCapitalization.sentences),
        const SizedBox(height: IbhSpace.s16),
        IbhCard(
          child: Column(children: [
            _kv('Taken', watDayTime(c.capturedAt)),
            _kv('GPS', '${c.lat.toStringAsFixed(4)}°N ${c.lon.toStringAsFixed(4)}°E · ±${c.accuracyM.round()} m'),
            _kv('Signature', 'Signed on this phone'),
          ]),
        ),
        const SizedBox(height: IbhSpace.s12),
        Text('The server will check the site boundary, the signature and whether the photo was used before.', style: IbhText.small.copyWith(color: IbhColors.muted)),
      ]),
      bottomNavigationBar: BottomActionBar(row: true, children: [
        OutlinedButton(onPressed: _retake, child: const Text('Retake')),
        FilledButton(onPressed: _save, child: const Text('Save')),
      ]),
    );
  }

  static Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(k, style: IbhText.body.copyWith(color: IbhColors.muted)),
          const SizedBox(width: IbhSpace.s12),
          Expanded(child: Text(v, textAlign: TextAlign.right, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink))),
        ]),
      );
}

const _label = TextStyle(fontFamily: 'Inter', fontSize: 15, fontWeight: FontWeight.w600, color: IbhColors.ink);
