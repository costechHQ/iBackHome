import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../core/wat.dart';
import '../theme/ibh_tokens.dart';
import '../ui/forms.dart';
import '../ui/ibh_app_bar.dart';
import '../ui/ibh_card.dart';
import '../ui/states.dart';
import 'home_screen.dart';
import 'widgets.dart';

/// True when the camera, location and the registered signing key are all ready.
Future<bool> captureReady(WidgetRef ref) async {
  if (!await Permission.camera.isGranted || !await Permission.locationWhenInUse.isGranted) return false;
  try {
    await ref.read(deviceProvider.future);
    return true;
  } catch (_) {
    return false;
  }
}

/// Used before any capture screen: opens AND-SUPERVISOR-002 if something is missing.
Future<bool> ensureCaptureReady(BuildContext context, WidgetRef ref) async {
  if (await captureReady(ref)) return true;
  if (!context.mounted) return false;
  final ok = await Navigator.of(context).push<bool>(MaterialPageRoute(builder: (_) => const PermissionsScreen()));
  return ok == true;
}

/// AND-SUPERVISOR-002: "Set up this phone", in two steps: camera and location permission, then
/// the signing key in the Keystore; then "Capture key ready".
class PermissionsScreen extends ConsumerStatefulWidget {
  const PermissionsScreen({super.key});

  @override
  ConsumerState<PermissionsScreen> createState() => _PermissionsScreenState();
}

class _PermissionsScreenState extends ConsumerState<PermissionsScreen> {
  PermissionStatus? _camera;
  PermissionStatus? _location;
  bool _gps = true;
  bool _busy = false;
  bool _ready = false; // the key is registered: show "Capture key ready"
  String? _keyError;

  bool get _permissionsOk => _camera?.isGranted == true && _location?.isGranted == true;
  bool get _denied => _camera?.isPermanentlyDenied == true || _location?.isPermanentlyDenied == true;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    final cam = await Permission.camera.status;
    final loc = await Permission.locationWhenInUse.status;
    final gps = await Geolocator.isLocationServiceEnabled();
    if (mounted) {
      setState(() {
        _camera = cam;
        _location = loc;
        _gps = gps;
      });
    }
  }

  Future<void> _allow() async {
    setState(() => _busy = true);
    await Permission.camera.request();
    await Permission.locationWhenInUse.request();
    await _refresh();
    if (mounted) setState(() => _busy = false);
  }

  Future<void> _createKey() async {
    setState(() {
      _busy = true;
      _keyError = null;
    });
    // Pressing "Create my capture key" is the person's decision to set this phone up (again).
    await ref.read(servicesProvider).tokens.setRevokedHere(false);
    ref.invalidate(deviceProvider);
    try {
      await ref.read(deviceProvider.future);
      if (mounted) setState(() => _ready = true);
    } catch (e) {
      if (mounted) setState(() => _keyError = ApiError.from(e).friendlyMessage);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _spinner() =>
      const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: IbhColors.white));

  @override
  Widget build(BuildContext context) {
    if (_ready) return _allSet();
    if (_camera == null) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return _permissionsOk ? _keyStep() : _permissionStep();
  }

  Widget _permissionStep() => Scaffold(
        backgroundColor: IbhColors.white,
        appBar: const IbhAppBar(title: 'Set up this phone', trailingText: '1 of 2'),
        body: Column(children: [
          const StepProgress(step: 1, of: 2),
          Expanded(
            child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
              Text('Allow what the camera needs', style: IbhText.h2.copyWith(fontSize: 26)),
              const SizedBox(height: IbhSpace.s12),
              const Text('Android will ask you next.', style: IbhText.bodyLg),
              const SizedBox(height: IbhSpace.s16),
              _need(Icons.photo_camera_outlined, 'Camera', 'Photos and video are taken only inside the app.', _camera?.isGranted == true),
              _need(Icons.place_outlined, 'Precise location', 'Proves each capture is inside the site. Mock or fake locations are blocked.', _location?.isGranted == true),
              if (!_gps)
                const Padding(
                  padding: EdgeInsets.only(top: IbhSpace.s12),
                  child: Alert('Location services are off. Turn on GPS in the phone settings.', tone: ChipTone.bad),
                ),
              if (_denied)
                const Padding(
                  padding: EdgeInsets.only(top: IbhSpace.s12),
                  child: Alert('A permission was turned off for good. Open the phone settings for iBackHome and allow it.', tone: ChipTone.bad),
                ),
            ]),
          ),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: _busy ? null : (_denied ? openAppSettings : _allow), child: _busy ? _spinner() : Text(_denied ? 'Open phone settings' : 'Allow')),
        ]),
      );

  Widget _need(IconData icon, String title, String detail, bool ok) => Container(
        padding: const EdgeInsets.symmetric(vertical: IbhSpace.s12),
        decoration: const BoxDecoration(border: Border(bottom: BorderSide(color: IbhColors.line))),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(color: IbhColors.mist, borderRadius: BorderRadius.circular(IbhRadius.control)),
            child: Icon(icon, size: 20),
          ),
          const SizedBox(width: IbhSpace.s12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: IbhText.body.copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink)),
              Text(detail, style: IbhText.small),
            ]),
          ),
          if (ok) const Padding(padding: EdgeInsets.only(left: 8), child: StatusChip('Allowed', tone: ChipTone.ok)),
        ]),
      );

  Widget _keyStep() => Scaffold(
        backgroundColor: IbhColors.white,
        appBar: const IbhAppBar(title: 'Set up this phone', trailingText: '2 of 2'),
        body: Column(children: [
          const StepProgress(step: 2, of: 2),
          Expanded(
            child: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
              const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.vpn_key_outlined)),
              const SizedBox(height: IbhSpace.s16),
              Text('Your secure capture key', style: IbhText.h2.copyWith(fontSize: 26)),
              const SizedBox(height: IbhSpace.s12),
              const Text('This phone gets its own key. It signs every photo and video you take, so nobody can fake or change them.', style: IbhText.bodyLg),
              const SizedBox(height: IbhSpace.s16),
              Container(
                padding: const EdgeInsets.all(IbhSpace.s16),
                decoration: BoxDecoration(color: IbhColors.mist, borderRadius: BorderRadius.circular(IbhRadius.card)),
                child: const Column(children: [
                  _Point(Icons.smartphone, 'Created on this phone. The private part never leaves it.'),
                  _Point(Icons.lock_outline, 'Signs each capture with the time and place it was taken.'),
                  _Point(Icons.cancel_outlined, 'Captures signed by an unknown or revoked key are rejected.'),
                  _Point(Icons.sync, 'New phone? Sign in there and create a new key; revoke the old one in Settings.'),
                ]),
              ),
              if (_keyError != null) ...[
                const SizedBox(height: IbhSpace.s12),
                Alert('The key could not be registered. $_keyError', tone: ChipTone.bad),
              ],
            ]),
          ),
        ]),
        bottomNavigationBar: BottomActionBar(children: [
          FilledButton(onPressed: _busy ? null : _createKey, child: _busy ? _spinner() : const Text('Create my capture key')),
        ]),
      );

  Widget _allSet() {
    final device = ref.read(servicesProvider).device;
    final id = (device?['device_id'] as String?) ?? '';
    final created = device?['registered_at'] as String?;
    return Scaffold(
      backgroundColor: IbhColors.white,
      appBar: const IbhAppBar(title: 'All set', leading: IbhBarLeading.none),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const Align(alignment: Alignment.centerLeft, child: IconBadge(Icons.check_circle_outline, ok: true)),
        const SizedBox(height: IbhSpace.s16),
        Text('Capture key ready', style: IbhText.h2.copyWith(fontSize: 26)),
        const SizedBox(height: IbhSpace.s12),
        const Text('This phone can now take evidence for iBackHome.', style: IbhText.bodyLg),
        const SizedBox(height: IbhSpace.s16),
        IbhCard(
          child: Column(children: [
            _kv('Key', id.length >= 4 ? 'ending ${id.substring(id.length - 4).toUpperCase()}' : 'registered', mono: true),
            if (created != null) _kv('Created', watDayTime(DateTime.parse(created))),
          ]),
        ),
      ]),
      bottomNavigationBar: BottomActionBar(children: [
        FilledButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('Go to my sites')),
      ]),
    );
  }

  Widget _kv(String k, String v, {bool mono = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Text(k, style: IbhText.body.copyWith(color: IbhColors.muted)),
          Flexible(child: Text(v, textAlign: TextAlign.right, style: (mono ? IbhText.mono : IbhText.body).copyWith(fontWeight: FontWeight.w700, color: IbhColors.ink))),
        ]),
      );
}

class _Point extends StatelessWidget {
  const _Point(this.icon, this.text);
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, size: 20),
          const SizedBox(width: IbhSpace.s12),
          Expanded(child: Text(text, style: IbhText.body)),
        ]),
      );
}
