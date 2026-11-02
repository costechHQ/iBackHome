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
import '../ui/sheets.dart';
import '../ui/states.dart';
import 'home_screen.dart';
import 'widgets.dart';

/// Photos and videos the server already holds that are still on this phone, and the space they take.
/// Clearing them is safe: only accepted captures count, and nothing waiting to upload is touched.
final _uploadedCopiesProvider = FutureProvider.autoDispose<({List<QueuedCapture> items, int bytes})>((ref) async {
  final all = await ref.read(servicesProvider).db.all();
  final items = <QueuedCapture>[];
  var bytes = 0;
  for (final c in all.where((c) => c.status == CaptureStatus.accepted)) {
    final f = File(c.filePath);
    if (await f.exists()) {
      items.add(c);
      bytes += await f.length();
    }
  }
  return (items: items, bytes: bytes);
});

String _mb(int bytes) => bytes < 1024 * 1024 ? '${(bytes / 1024).ceil()} KB' : '${(bytes / (1024 * 1024)).toStringAsFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB';

/// AND-SUPERVISOR-015: settings. Time is Nigerian time for these roles, spot-check SMS cannot be
/// turned off, and revoking this phone is the one destructive action, so it sits behind a red button
/// inside a sheet.
///
/// Not here yet, on purpose: a push-notification switch and "hide previews" (there is no push yet), a
/// list of old phones to revoke (no devices list route, MX-12), and "download my data" (no route).
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final name = auth.me?['full_name'] as String?;
    final copies = ref.watch(_uploadedCopiesProvider).value;
    return Scaffold(
      appBar: IbhAppBar(title: 'Settings', subtitle: name),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        if (auth.isSupervisor) ...[
          const IbhSectionLabel('NOTIFICATIONS'),
          const IbhGroup(children: [
            IbhRow(
              title: 'SMS for spot checks',
              subtitle: 'Required, can\'t be turned off',
              trailing: Icon(Icons.lock_outline, color: IbhColors.muted),
            ),
          ]),
        ],
        const IbhSectionLabel('REGION'),
        const IbhGroup(children: [
          IbhRow(title: 'Time zone', subtitle: 'Nigerian time (WAT) · same as your sites'),
        ]),
        const IbhSectionLabel('DEVICES'),
        const _ThisPhone(),
        const SizedBox(height: IbhSpace.s8),
        Text(
          'Moving to a new phone? Sign in there and create its capture key. A list of your old phones isn\'t in the app yet.',
          style: IbhText.small.copyWith(color: IbhColors.muted),
        ),
        const IbhSectionLabel('DATA'),
        IbhGroup(children: [
          IbhRow(
            title: 'Clear uploaded copies',
            subtitle: copies == null ? 'Checking…' : '${_mb(copies.bytes)} · nothing unsent is deleted',
            trailing: const Icon(Icons.chevron_right),
            onTap: copies == null || copies.items.isEmpty ? null : () => _clear(context, ref, copies.items, copies.bytes),
          ),
        ]),
      ]),
    );
  }

  Future<void> _clear(BuildContext context, WidgetRef ref, List<QueuedCapture> items, int bytes) async {
    final go = await confirmSheet(
      context,
      title: 'Clear uploaded copies?',
      message: 'This frees ${_mb(bytes)} on the phone. It only removes copies the server has already accepted. Nothing waiting to upload is deleted.',
      confirmLabel: 'Clear copies',
      cancelLabel: 'Keep them',
    );
    if (!go) return;
    for (final c in items) {
      try {
        await File(c.filePath).delete();
      } catch (_) {}
    }
    ref.invalidate(_uploadedCopiesProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text('Freed ${_mb(bytes)}.')));
    }
  }
}

class _ThisPhone extends ConsumerWidget {
  const _ThisPhone();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final device = ref.watch(deviceProvider);
    final s = ref.read(servicesProvider);
    return device.when(
      loading: () => const SizedBox(height: 120, child: SkeletonList(rows: 1)),
      error: (e, _) => IbhCard(child: Text(ApiError.from(e).friendlyMessage, style: IbhText.body)),
      data: (id) {
        final created = s.device?['registered_at'] as String?;
        return IbhGroup(children: [
          IbhRow(
            leading: const Icon(Icons.smartphone),
            title: 'This phone',
            subtitle: created == null ? 'Signing key ready' : 'Signing key since ${watDay(DateTime.parse(created))}',
            trailing: const StatusChip('Active', tone: ChipTone.info),
          ),
          IbhRow(
            title: 'Revoke this phone',
            subtitle: 'For a lost or replaced phone',
            trailing: OutlinedButton(
              style: OutlinedButton.styleFrom(minimumSize: const Size(96, 48)),
              onPressed: () => _revoke(context, ref),
              child: const Text('Revoke'),
            ),
          ),
        ]);
      },
    );
  }

  Future<void> _revoke(BuildContext context, WidgetRef ref) async {
    final go = await confirmSheet(
      context,
      title: 'Revoke this phone?',
      message: 'Its signing key stops working at once, so nothing taken on it can be uploaded as you. Captures still waiting to upload will be rejected by the server. You can set the phone up again with a new key.',
      confirmLabel: 'Revoke device',
      destructive: true,
      footnote: 'To use a different phone, sign in there and create a new key.',
    );
    if (!go) return;
    try {
      await ref.read(servicesProvider).revokeThisPhone();
      ref.invalidate(deviceProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(const SnackBar(content: Text('This phone was revoked. Its signing key no longer works.')));
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }
}

