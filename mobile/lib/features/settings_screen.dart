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
final uploadedCopiesProvider = FutureProvider.autoDispose<({List<QueuedCapture> items, int bytes})>((ref) async {
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

String formatBytes(int bytes) => bytes < 1024 * 1024 ? '${(bytes / 1024).ceil()} KB' : '${(bytes / (1024 * 1024)).toStringAsFixed(bytes < 10 * 1024 * 1024 ? 1 : 0)} MB';

/// AND-SUPERVISOR-015: settings. Time is Nigerian time for these roles, spot-check SMS cannot be
/// turned off, and revoking this phone is the one destructive action, so it sits behind a red button
/// inside a sheet.
///
/// Not here yet, on purpose: a push-notification switch and "hide previews" (there is no push yet) and
/// "download my data" (no route). The old-phones list reads `GET /devices` (MX-12).
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final name = auth.me?['full_name'] as String?;
    final copies = ref.watch(uploadedCopiesProvider).value;
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
        const _OtherPhones(),
        const SizedBox(height: IbhSpace.s8),
        Text(
          'Moving to a new phone? Sign in there and create its capture key. Revoke the old one here so it can never capture as you.',
          style: IbhText.small.copyWith(color: IbhColors.muted),
        ),
        const IbhSectionLabel('DATA'),
        IbhGroup(children: [
          IbhRow(
            title: 'Clear uploaded copies',
            subtitle: copies == null ? 'Checking…' : '${formatBytes(copies.bytes)} · nothing unsent is deleted',
            trailing: const Icon(Icons.chevron_right),
            onTap: copies == null || copies.items.isEmpty ? null : () => clearCopies(context, ref, copies.items, copies.bytes),
          ),
        ]),
      ]),
    );
  }

  static Future<void> clearCopies(BuildContext context, WidgetRef ref, List<QueuedCapture> items, int bytes) async {
    final go = await confirmSheet(
      context,
      title: 'Clear uploaded copies?',
      message: 'This frees ${formatBytes(bytes)} on the phone. It only removes copies the server has already accepted. Nothing waiting to upload is deleted.',
      confirmLabel: 'Clear copies',
      cancelLabel: 'Keep them',
    );
    if (!go) return;
    for (final c in items) {
      try {
        await File(c.filePath).delete();
      } catch (_) {}
    }
    ref.invalidate(uploadedCopiesProvider);
    if (context.mounted) {
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text('Freed ${formatBytes(bytes)}.')));
    }
  }
}

/// The person's phones other than this one, read live from the server.
///
/// No automatic retry: a failure shows at once with its own Retry button, instead of a loading
/// skeleton while Riverpod backs off for several seconds.
final otherPhonesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) async {
    final s = ref.read(servicesProvider);
    final mine = s.device?['id'] as String?;
    final all = await s.listDevices();
    return [
      for (final d in all)
        if (d['id'] != mine) d,
    ];
  },
  retry: (_, _) => null,
);

/// AND-SUPERVISOR-015 "Devices": old phones with the time they were set up and, for an active one, a
/// Revoke button. Revoking another phone only ends its signing key; nothing on this phone changes.
class _OtherPhones extends ConsumerWidget {
  const _OtherPhones();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final phones = ref.watch(otherPhonesProvider);
    return phones.when(
      loading: () => const Padding(padding: EdgeInsets.only(top: IbhSpace.s8), child: SizedBox(height: 56, child: SkeletonList(rows: 1))),
      error: (e, _) => Padding(
        padding: const EdgeInsets.only(top: IbhSpace.s8),
        child: IbhCard(
          child: Row(children: [
            Expanded(child: Text('Your other phones couldn\'t be loaded. ${ApiError.from(e).friendlyMessage}', style: IbhText.small)),
            TextButton(onPressed: () => ref.invalidate(otherPhonesProvider), child: const Text('Retry')),
          ]),
        ),
      ),
      data: (items) => items.isEmpty
          ? Padding(
              padding: const EdgeInsets.only(top: IbhSpace.s8),
              child: Text('No other phones are set up on your account.', style: IbhText.small.copyWith(color: IbhColors.muted)),
            )
          : Padding(
              padding: const EdgeInsets.only(top: IbhSpace.s8),
              child: IbhGroup(children: [for (final d in items) _phoneRow(context, ref, d)]),
            ),
    );
  }

  Widget _phoneRow(BuildContext context, WidgetRef ref, Map<String, dynamic> d) {
    final revoked = d['revoked_at'] != null;
    final when = DateTime.parse(d['registered_at'] as String);
    return IbhRow(
      leading: Icon(revoked ? Icons.phonelink_erase : Icons.smartphone_outlined, color: revoked ? IbhColors.muted : IbhColors.ink),
      title: 'Another phone',
      subtitle: revoked
          ? 'Set up ${watDay(when)} · revoked ${watDay(DateTime.parse(d['revoked_at'] as String))}'
          : 'Signing key since ${watDay(when)}',
      trailing: revoked
          ? const StatusChip('Revoked', tone: ChipTone.neutral)
          : OutlinedButton(
              style: OutlinedButton.styleFrom(minimumSize: const Size(96, 48)),
              onPressed: () => _revoke(context, ref, d['id'] as String),
              child: const Text('Revoke'),
            ),
    );
  }

  Future<void> _revoke(BuildContext context, WidgetRef ref, String pk) async {
    final go = await confirmSheet(
      context,
      title: 'Revoke this other phone?',
      message: 'Its signing key stops working at once. Anything still waiting to upload from that phone will be rejected by the server. This phone is not affected.',
      confirmLabel: 'Revoke phone',
      destructive: true,
    );
    if (!go) return;
    try {
      await ref.read(servicesProvider).revokeOtherDevice(pk);
      ref.invalidate(otherPhonesProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(const SnackBar(content: Text('That phone was revoked. Its signing key no longer works.')));
      }
    } catch (e) {
      if (context.mounted) showError(context, e);
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

