import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/capture_rules.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'widgets.dart';

/// AND-SUPERVISOR-007, the Sync tab: every capture and decision on this phone and where it stands.
/// Rows show an icon, not a photo (lists load no images on low-end phones); the photo opens in the
/// detail sheet. A rejection always says why.
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
    if (!_loaded) return const SkeletonList();
    final sync = _s.sync;
    final waiting = _items.where((c) => CaptureStatus.open.contains(c.status)).length + _actions.where((a) => a.status == 'queued').length;
    final old = _items.where((c) => c.status == CaptureStatus.queued && c.uploadDueSoon && !c.windowLeft.isNegative).length;
    final retrying = _items.any((c) => c.status == CaptureStatus.queued && c.attempts > 0);
    if (_items.isEmpty && _actions.isEmpty) {
      final at = sync.lastSyncedAt;
      return EmptyState(
        icon: Icons.check_circle_outline,
        title: 'Everything uploaded',
        message: at == null ? 'Nothing is waiting on this phone.' : 'Last synced ${watClock(at)}. Nothing is waiting on this phone.',
      );
    }
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      if (old > 0) ...[
        _UploadSoon(old),
        const SizedBox(height: IbhSpace.s12),
      ],
      Row(children: [
        Expanded(child: Text(waiting == 0 ? 'Nothing waiting to upload' : '$waiting waiting to upload', style: IbhText.h3.copyWith(fontSize: 18))),
        TextButton(
          onPressed: sync.running ? null : () => sync.syncNow(force: true),
          child: Text(sync.running ? 'Syncing…' : (retrying ? 'Retry all now' : 'Sync now'), style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
      ]),
      const SizedBox(height: IbhSpace.s8),
      IbhGroup(children: [
        for (final a in _actions) _ActionRow(a, onDismiss: () async {
          await _s.db.deleteAction(a.id);
          await _load();
        }),
        for (final c in _items) _CaptureRow(c, onTap: () => _open(c)),
      ]),
      const SizedBox(height: IbhSpace.s12),
      Text(
        'Everything is stored on the phone and signed. It uploads by itself the moment there\'s signal; Wi-Fi isn\'t needed.',
        style: IbhText.small.copyWith(color: IbhColors.muted),
      ),
    ]);
  }

  void _open(QueuedCapture c) => showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        showDragHandle: true,
        backgroundColor: IbhColors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(IbhRadius.sheet))),
        builder: (_) => _CaptureSheet(c, onRetry: () {
          Navigator.of(context).pop();
          _s.sync.syncNow(force: true);
        }),
      );
}

({String label, ChipTone tone}) _chip(String status) => switch (status) {
      CaptureStatus.accepted => (label: 'Accepted', tone: ChipTone.ok),
      CaptureStatus.flagged => (label: 'Flagged', tone: ChipTone.warn),
      CaptureStatus.rejected => (label: 'Rejected', tone: ChipTone.bad),
      CaptureStatus.failed => (label: 'Needs attention', tone: ChipTone.bad),
      CaptureStatus.submitted => (label: 'Checking', tone: ChipTone.info),
      CaptureStatus.draft => (label: 'Not saved', tone: ChipTone.warn),
      _ => (label: 'Queued', tone: ChipTone.neutral),
    };

String _title(QueuedCapture c) =>
    c.checklistItem ?? (c.kind == 'video' ? 'Walkthrough video' : 'Photo');

class _Tile extends StatelessWidget {
  const _Tile(this.icon);
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(color: IbhColors.placeholder, borderRadius: BorderRadius.circular(IbhRadius.control)),
        child: Icon(icon, color: IbhColors.muted),
      );
}

class _UploadSoon extends StatelessWidget {
  const _UploadSoon(this.count);
  final int count;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(IbhSpace.s16),
        decoration: BoxDecoration(
          color: IbhColors.warnBg,
          borderRadius: BorderRadius.circular(IbhRadius.control),
          border: const Border(left: BorderSide(color: IbhColors.warnFg, width: 4)),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.schedule, color: IbhColors.warnFg),
          const SizedBox(width: IbhSpace.s12),
          Expanded(
            child: Text.rich(TextSpan(style: IbhText.body.copyWith(color: IbhColors.ink), children: [
              const TextSpan(text: 'Upload soon. ', style: TextStyle(fontWeight: FontWeight.w700)),
              TextSpan(
                  text: '$count capture${count == 1 ? ' is' : 's are'} more than 48 hours old. Anything not uploaded within 72 hours of being taken is rejected, and you\'d have to go back.'),
            ])),
          ),
        ]),
      );
}

class _CaptureRow extends StatelessWidget {
  const _CaptureRow(this.c, {required this.onTap});
  final QueuedCapture c;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final chip = _chip(c.status);
    final ref = c.evidenceId == null ? 'waiting' : 'EV-${c.evidenceId!.substring(0, 4).toUpperCase()}';
    final age = c.status == CaptureStatus.queued ? ' · ${DateTime.now().toUtc().difference(c.capturedAt).inHours} h' : '';
    final extra = (c.status == CaptureStatus.flagged || c.status == CaptureStatus.rejected || c.status == CaptureStatus.failed) ? c.reason : null;
    return IbhRow(
      onTap: onTap,
      leading: _Tile(c.kind == 'video' ? Icons.videocam_outlined : Icons.photo_camera_outlined),
      title: _title(c),
      subtitle: '$ref · taken ${watClock(c.capturedAt)}$age${extra == null ? '' : '\n$extra'}',
      trailing: StatusChip(chip.label, tone: chip.tone),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow(this.a, {required this.onDismiss});
  final QueuedAction a;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final failed = a.status == 'failed';
    final saved = DateTime.fromMillisecondsSinceEpoch(a.createdAt, isUtc: true);
    return IbhRow(
      leading: const _Tile(Icons.fact_check_outlined),
      title: a.label,
      subtitle: failed
          ? (a.reason ?? 'It could not be sent.')
          : 'Saved ${watClock(saved)}${a.kind == 'verify' ? ' · sent when your photos are accepted' : ''}',
      trailing: failed
          ? TextButton(onPressed: onDismiss, child: const Text('Dismiss', style: TextStyle(fontWeight: FontWeight.w700)))
          : const StatusChip('Queued', tone: ChipTone.neutral),
    );
  }
}

class _CaptureSheet extends StatelessWidget {
  const _CaptureSheet(this.c, {required this.onRetry});
  final QueuedCapture c;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final chip = _chip(c.status);
    final left = c.windowLeft;
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(IbhSpace.s16, 0, IbhSpace.s16, IbhSpace.s16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(_title(c), style: IbhText.h3)),
            StatusChip(chip.label, tone: chip.tone),
          ]),
          if (c.asContractor) ...[
            const SizedBox(height: IbhSpace.s8),
            const StatusChip('Uploaded by the contractor', tone: ChipTone.neutral),
          ],
          const SizedBox(height: IbhSpace.s12),
          ClipRRect(
            borderRadius: BorderRadius.circular(IbhRadius.card),
            child: c.kind == 'video'
                ? Container(height: 160, color: IbhColors.camera, alignment: Alignment.center, child: const Icon(Icons.videocam, color: IbhColors.white, size: 48))
                : Image.file(File(c.filePath),
                    height: 220,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => Container(height: 120, color: IbhColors.placeholder, alignment: Alignment.center, child: const Icon(Icons.image_not_supported))),
          ),
          const SizedBox(height: IbhSpace.s12),
          Text('Taken ${watDayTime(c.capturedAt)}', style: IbhText.body),
          if (c.note != null) Text('Note: ${c.note}', style: IbhText.body),
          if (c.reason != null) ...[
            const SizedBox(height: IbhSpace.s8),
            Text(c.reason!, style: IbhText.body.copyWith(color: IbhColors.badFg, fontWeight: FontWeight.w600)),
          ],
          if (c.status == CaptureStatus.queued && c.uploadDueSoon) ...[
            const SizedBox(height: IbhSpace.s8),
            Text(
              left.isNegative ? 'Past the 72 h upload window: the server will reject it.' : 'Upload within ${left.inHours} h or the server will reject it.',
              style: IbhText.body.copyWith(color: IbhColors.warnFg, fontWeight: FontWeight.w600),
            ),
          ],
          const SizedBox(height: IbhSpace.s12),
          ThreeChecksView(ThreeChecks.from(c.status, c.reason)),
          if (c.status == CaptureStatus.queued || c.status == CaptureStatus.failed) ...[
            const SizedBox(height: IbhSpace.s16),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry now')),
          ],
        ]),
      ),
    );
  }
}
