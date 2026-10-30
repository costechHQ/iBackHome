import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/capture_rules.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
import 'capture_screen.dart' show captureStatusLabel;
import 'widgets.dart';

/// AND-SUPERVISOR-007: every capture on this phone and where it stands.
class QueueScreen extends ConsumerStatefulWidget {
  const QueueScreen({super.key});

  @override
  ConsumerState<QueueScreen> createState() => _QueueScreenState();
}

class _QueueScreenState extends ConsumerState<QueueScreen> {
  late final Services _s = ref.read(servicesProvider);
  List<QueuedCapture> _items = const [];
  List<QueuedAction> _actions = const [];
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    _s.sync.addListener(_load);
    _load();
  }

  @override
  void dispose() {
    _s.sync.removeListener(_load);
    super.dispose();
  }

  Future<void> _load() async {
    final items = await _s.db.all();
    final actions = await _s.db.actions();
    if (!mounted) return;
    setState(() {
      _items = items;
      _actions = actions.where((a) => a.status != 'done').toList();
      _loaded = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) return const Center(child: CircularProgressIndicator());
    final sync = _s.sync;
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(IbhSpace.s16),
        child: Row(children: [
          Expanded(child: Text('${_items.where((c) => CaptureStatus.open.contains(c.status)).length} waiting')),
          FilledButton.tonal(
            onPressed: sync.running ? null : () => sync.syncNow(force: true),
            child: Text(sync.running ? 'Syncing...' : 'Sync now'),
          ),
        ]),
      ),
      for (final a in _actions)
        ListTile(
          leading: Icon(a.status == 'failed' ? Icons.error_outline : Icons.schedule,
              color: a.status == 'failed' ? IbhColors.badFg : IbhColors.muted),
          title: Text(a.label),
          subtitle: Text(a.status == 'failed'
              ? (a.reason ?? 'Could not be sent.')
              : 'Waiting to be sent when you have signal${a.kind == 'verify' ? ' and your photos are accepted' : ''}.'),
          trailing: a.status == 'failed'
              ? TextButton(
                  onPressed: () async {
                    await _s.db.deleteAction(a.id);
                    await _load();
                  },
                  child: const Text('Dismiss'))
              : null,
        ),
      Expanded(
        child: _items.isEmpty
            ? const Center(child: Text('Nothing captured on this phone yet.'))
            : ListView.separated(
                itemCount: _items.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (_, i) => _CaptureTile(_items[i]),
              ),
      ),
    ]);
  }
}

class _CaptureTile extends StatelessWidget {
  const _CaptureTile(this.c);
  final QueuedCapture c;

  @override
  Widget build(BuildContext context) {
    final tone = switch (c.status) {
      CaptureStatus.accepted => ChipTone.ok,
      CaptureStatus.flagged || CaptureStatus.draft => ChipTone.warn,
      CaptureStatus.rejected || CaptureStatus.failed => ChipTone.bad,
      CaptureStatus.submitted => ChipTone.info,
      _ => ChipTone.neutral,
    };
    final left = c.windowLeft;
    final waiting = c.status == CaptureStatus.queued;
    return Padding(
      padding: const EdgeInsets.all(IbhSpace.s12),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(IbhRadius.control),
          child: c.kind == 'video'
              ? const SizedBox(width: 64, height: 64, child: ColoredBox(color: IbhColors.camera, child: Icon(Icons.videocam, color: IbhColors.white)))
              : Image.file(File(c.filePath),
                  width: 64,
                  height: 64,
                  fit: BoxFit.cover,
                  errorBuilder: (_, _, _) =>
                      const SizedBox(width: 64, height: 64, child: Icon(Icons.image_not_supported))),
        ),
        const SizedBox(width: IbhSpace.s12),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(spacing: 6, runSpacing: 4, children: [
              StatusChip(captureStatusLabel(c.status), tone: tone),
              if (c.asContractor) const StatusChip('Uploaded by the contractor', tone: ChipTone.neutral),
            ]),
            const SizedBox(height: 4),
            Text('Taken ${c.capturedAt.toLocal().toString().substring(0, 16)}', style: IbhText.small),
            if (c.checklistItem != null) Text(c.checklistItem!, style: IbhText.small),
            if (c.note != null) Text('Note: ${c.note}', style: IbhText.small),
            if (c.reason != null)
              Text(c.reason!, style: const TextStyle(color: IbhColors.badFg, fontSize: 13)),
            if (waiting && left < const Duration(hours: 24))
              Text(
                  left.isNegative
                      ? 'Past the 72 h upload window: the server will reject it.'
                      : 'Upload within ${left.inHours} h or the server will reject it.',
                  style: const TextStyle(color: IbhColors.warnFg, fontSize: 13)),
            const SizedBox(height: 6),
            ThreeChecksView(ThreeChecks.from(c.status, c.reason)),
          ]),
        ),
      ]),
    );
  }
}
