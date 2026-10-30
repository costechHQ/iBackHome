import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/queue_db.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
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
    if (!mounted) return;
    setState(() {
      _items = items;
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
    final (label, tone) = switch (c.status) {
      CaptureStatus.accepted => ('Accepted', ChipTone.ok),
      CaptureStatus.flagged => ('Flagged for review', ChipTone.warn),
      CaptureStatus.rejected => ('Rejected', ChipTone.bad),
      CaptureStatus.failed => ('Needs attention', ChipTone.bad),
      CaptureStatus.submitted => ('Server checking', ChipTone.info),
      _ => ('Waiting to upload', ChipTone.neutral),
    };
    final left = c.windowLeft;
    final urgent = c.status == CaptureStatus.queued && left < const Duration(hours: 24);
    return ListTile(
      leading: ClipRRect(
        borderRadius: BorderRadius.circular(IbhRadius.control),
        child: Image.file(File(c.filePath),
            width: 56,
            height: 56,
            fit: BoxFit.cover,
            errorBuilder: (_, _, _) =>
                const SizedBox(width: 56, height: 56, child: Icon(Icons.image_not_supported))),
      ),
      title: Align(alignment: Alignment.centerLeft, child: StatusChip(label, tone: tone)),
      subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Taken ${c.capturedAt.toLocal().toString().substring(0, 16)}'),
        if (c.reason != null) Text(c.reason!, style: const TextStyle(color: IbhColors.badFg)),
        if (urgent)
          Text(left.isNegative ? 'Past the 72 h upload window' : '${left.inHours} h left to upload',
              style: const TextStyle(color: IbhColors.warnFg)),
      ]),
    );
  }
}
