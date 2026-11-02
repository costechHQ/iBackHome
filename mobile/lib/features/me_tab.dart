import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_error.dart';
import '../core/free_space.dart';
import '../core/queue_db.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import 'home_screen.dart';
import 'payout_screen.dart';
import 'permissions_screen.dart';
import 'profile_screen.dart';
import 'queue_screen.dart';
import 'settings_screen.dart';
import 'vetting_screen.dart';
import 'widgets.dart';

/// Captures not yet uploaded and the space their files take: what the Storage row shows.
final _storageProvider = FutureProvider.autoDispose<({int waiting, int bytes})>((ref) async {
  final all = await ref.read(servicesProvider).db.all();
  var bytes = 0;
  var waiting = 0;
  for (final c in all) {
    if (CaptureStatus.open.contains(c.status) || c.status == CaptureStatus.draft) {
      waiting++;
      try {
        bytes += await File(c.filePath).length();
      } catch (_) {}
    }
  }
  return (waiting: waiting, bytes: bytes);
});

/// Free space on the phone, read again each time the Me tab opens.
final freeSpaceProvider = FutureProvider.autoDispose<int?>((ref) => FreeSpace.freeBytes());

/// The "storage almost full" panel (AND-SUPERVISOR-012, state 2): what is waiting, what is safe to
/// clear, and the two ways out. Shown below [FreeSpace.warnBytes]; below [FreeSpace.stopBytes] the
/// camera refuses to capture.
class _StorageLow extends ConsumerWidget {
  const _StorageLow(this.free, this.waiting);
  final int free;
  final ({int waiting, int bytes})? waiting;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final copies = ref.watch(uploadedCopiesProvider).value;
    final full = FreeSpace.level(free) == StorageLevel.full;
    final sync = ref.read(servicesProvider).sync;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Alert(
        full
            ? 'Phone storage is full: ${formatBytes(free)} free. The camera is stopped until you free some space.'
            : 'Phone storage almost full: ${formatBytes(free)} free. Captures stay on the phone until they upload. Below ${formatBytes(FreeSpace.stopBytes)} the camera stops.',
        tone: full ? ChipTone.bad : ChipTone.warn,
      ),
      const SizedBox(height: IbhSpace.s12),
      IbhCard(
        child: Column(children: [
          _line('Waiting to upload', waiting == null ? '…' : '${waiting!.waiting} item${waiting!.waiting == 1 ? '' : 's'} · ${formatBytes(waiting!.bytes)}'),
          _line('Already uploaded, safe to clear', copies == null ? '…' : formatBytes(copies.bytes)),
        ]),
      ),
      const SizedBox(height: IbhSpace.s12),
      FilledButton.icon(
        onPressed: () => sync.syncNow(force: true),
        icon: const Icon(Icons.cloud_upload_outlined),
        label: const Text('Upload now'),
      ),
      const SizedBox(height: IbhSpace.s8),
      OutlinedButton(
        onPressed: copies == null || copies.items.isEmpty
            ? null
            : () async {
                await SettingsScreen.clearCopies(context, ref, copies.items, copies.bytes);
                ref.invalidate(freeSpaceProvider);
              },
        child: const Text('Clear uploaded copies'),
      ),
      const SizedBox(height: IbhSpace.s8),
      Text(
        'Clearing only removes copies the server has accepted. Nothing waiting to upload is deleted.',
        style: IbhText.small.copyWith(color: IbhColors.muted),
      ),
      const SizedBox(height: IbhSpace.s16),
    ]);
  }

  static Widget _line(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          Expanded(child: Text(k, style: IbhText.body.copyWith(color: IbhColors.muted))),
          Text(v, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
        ]),
      );
}

/// AND-SUPERVISOR-012, the Me tab (Account for a contractor): who you are, vetting, this phone's
/// signing key, and what is waiting to upload. Time is always Nigerian time (WAT), so there is no
/// time-zone setting for these roles.
class MeTab extends ConsumerWidget {
  const MeTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authProvider);
    final me = auth.me ?? const {};
    final name = (me['full_name'] as String?)?.trim();
    final vetting = auth.isSupervisor ? ref.watch(vettingProvider).value : null;
    final storage = ref.watch(_storageProvider).value;
    final free = ref.watch(freeSpaceProvider).value;
    return ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
      if (free != null && FreeSpace.level(free) != StorageLevel.ok) _StorageLow(free, storage),
      IbhCard(
        child: Row(children: [
          Container(
            width: 56,
            height: 56,
            alignment: Alignment.center,
            decoration: const BoxDecoration(color: IbhColors.neutralBg, shape: BoxShape.circle),
            child: Text(_initials(name), style: IbhText.h3),
          ),
          const SizedBox(width: IbhSpace.s12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name == null || name.isEmpty ? 'Your account' : name, style: IbhText.h3.copyWith(fontSize: 18)),
              Text(
                auth.isSupervisor && vetting != null ? '${vetting['registration_body']} registered' : '${me['phone'] ?? me['email'] ?? ''}',
                style: IbhText.small,
              ),
            ]),
          ),
          if (auth.isSupervisor && vetting != null) StatusChip(vetting['vetting_status'] == 'approved' ? 'Vetted' : 'Under review', tone: vetting['vetting_status'] == 'approved' ? ChipTone.ok : ChipTone.warn),
        ]),
      ),
      const SizedBox(height: IbhSpace.s12),
      IbhGroup(children: [
        IbhRow(
          leading: const Icon(Icons.person_outline),
          title: 'Profile',
          subtitle: 'Your name and sign-in details',
          trailing: const Icon(Icons.chevron_right),
          onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const ProfileScreen())),
        ),
        IbhRow(
          leading: const Icon(Icons.settings_outlined),
          title: 'Settings',
          subtitle: 'Notifications, devices and data',
          trailing: const Icon(Icons.chevron_right),
          onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
        ),
        if (auth.isSupervisor && vetting != null && vetting['vetting_status'] == 'approved')
          IbhRow(
            leading: const Icon(Icons.verified_user_outlined),
            title: 'Vetting',
            subtitle: vetting['vetted_at'] == null ? 'Approved by iBackHome' : 'Approved by iBackHome, ${watDay(DateTime.parse(vetting['vetted_at'] as String))}',
          ),
        if (auth.isContractor)
          IbhRow(
            leading: const Icon(Icons.account_balance_outlined),
            title: 'Payout account',
            subtitle: 'Where your releases are paid',
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const PayoutScreen())),
          ),
        if (auth.isContractor)
          IbhRow(
            leading: const Icon(Icons.cloud_upload_outlined),
            title: 'Sync',
            subtitle: storage == null ? 'Captures on this phone' : (storage.waiting == 0 ? 'Everything uploaded' : '${storage.waiting} waiting to upload'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
              builder: (_) => const Scaffold(appBar: IbhAppBar(title: 'Sync', subtitle: 'Captures and decisions on this phone'), body: QueueScreen()),
            )),
          ),
        IbhRow(
          leading: const Icon(Icons.sd_storage_outlined),
          title: 'Storage',
          subtitle: storage == null ? 'Checking…' : '${storage.waiting} item${storage.waiting == 1 ? '' : 's'} waiting · ${formatBytes(storage.bytes)}',
        ),
      ]),
      const IbhSectionLabel('THIS PHONE'),
      const _PhoneCard(),
      const SizedBox(height: IbhSpace.s16),
      Text('Times are shown in Nigerian time (WAT). Held by a licensed escrow partner, never by iBackHome.', style: IbhText.small.copyWith(color: IbhColors.muted)),
      const SizedBox(height: IbhSpace.s8),
      TextButton(
        style: TextButton.styleFrom(minimumSize: const Size.fromHeight(48)),
        onPressed: () => confirmSignOut(context, ref),
        child: const Text('Sign out', style: TextStyle(fontWeight: FontWeight.w700)),
      ),
    ]);
  }

  static String _initials(String? name) {
    final parts = (name ?? '').trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '·';
    return (parts.first[0] + (parts.length > 1 ? parts.last[0] : '')).toUpperCase();
  }
}

/// The registered phone: its signing key, the revoke button (inside a dialog), and the revoked state.
class _PhoneCard extends ConsumerWidget {
  const _PhoneCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final device = ref.watch(deviceProvider);
    final s = ref.read(servicesProvider);
    return device.when(
      loading: () => const IbhCard(child: LinearProgressIndicator()),
      error: (e, _) {
        final err = ApiError.from(e);
        if (err.code == 'device_revoked_here') {
          return IbhCard(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const StatusChip('Signing key revoked', tone: ChipTone.bad),
              const SizedBox(height: IbhSpace.s8),
              Text(err.message, style: IbhText.body),
              const SizedBox(height: IbhSpace.s12),
              FilledButton(
                onPressed: () async {
                  await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const PermissionsScreen()));
                  ref.invalidate(deviceProvider);
                },
                child: const Text('Set up this phone again'),
              ),
            ]),
          );
        }
        return IbhCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Alert(err.message, tone: ChipTone.bad),
            TextButton(onPressed: () => ref.invalidate(deviceProvider), child: const Text('Try again')),
          ]),
        );
      },
      data: (id) {
        final created = s.device?['registered_at'] as String?;
        return IbhCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.smartphone),
              const SizedBox(width: IbhSpace.s12),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Registered phone', style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
                  Text(created == null ? 'Signing key ready' : 'Signing key made ${watDayTime(DateTime.parse(created))}', style: IbhText.small),
                ]),
              ),
              const StatusChip('This phone', tone: ChipTone.info),
            ]),
            const SizedBox(height: IbhSpace.s8),
            Text(id.length > 12 ? 'Key ending ${id.substring(id.length - 4).toUpperCase()}' : id, style: IbhText.mono.copyWith(fontSize: 12)),
          ]),
        );
      },
    );
  }
}
