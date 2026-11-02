import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';

/// The strip under the app bar on the main tabs. It always says where the phone's evidence stands:
/// "Everything uploaded · synced 08:32", "3 waiting to upload", or a dark offline banner.
/// The project list works offline from the last sync, so this strip says when that was.
class SyncStrip extends ConsumerStatefulWidget {
  const SyncStrip({super.key});

  @override
  ConsumerState<SyncStrip> createState() => _SyncStripState();
}

class _SyncStripState extends ConsumerState<SyncStrip> {
  late final Services _s = ref.read(servicesProvider);
  int _waiting = 0;

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
    final n = await _s.db.unsentCount();
    if (mounted) setState(() => _waiting = n);
  }

  @override
  Widget build(BuildContext context) {
    final sync = _s.sync;
    if (!sync.online) {
      return Container(
        width: double.infinity,
        color: IbhColors.navy900,
        padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s16, vertical: IbhSpace.s8),
        child: Row(children: [
          const Icon(Icons.cloud_off, size: 18, color: IbhColors.white),
          const SizedBox(width: IbhSpace.s8),
          const Expanded(
            child: Text(
              'Offline. Everything is saved on the phone and will upload when you\'re back online.',
              style: TextStyle(color: IbhColors.white, fontSize: 14, fontWeight: FontWeight.w600),
            ),
          ),
        ]),
      );
    }
    final synced = sync.lastSyncedAt;
    final (icon, color, text) = _waiting > 0
        ? (Icons.schedule, IbhColors.warnFg, '$_waiting waiting to upload')
        : (
            Icons.check_circle_outline,
            IbhColors.okFg,
            synced == null ? 'Everything uploaded' : 'Everything uploaded · synced ${watClock(synced)}'
          );
    return Container(
      width: double.infinity,
      decoration: const BoxDecoration(color: IbhColors.white, border: Border(bottom: BorderSide(color: IbhColors.line))),
      padding: const EdgeInsets.symmetric(horizontal: IbhSpace.s16, vertical: IbhSpace.s12),
      child: Row(children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(width: IbhSpace.s8),
        Expanded(child: Text(text, style: TextStyle(color: color, fontSize: 14, fontWeight: FontWeight.w600))),
      ]),
    );
  }
}
