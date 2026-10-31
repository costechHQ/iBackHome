import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

import '../core/api_error.dart';
import '../core/services.dart';
import '../theme/ibh_tokens.dart';
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

/// AND-SUPERVISOR-002: camera and location permission, then the signing key in the Keystore.
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
  String? _keyError;

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
    setState(() {
      _busy = true;
      _keyError = null;
    });
    await Permission.camera.request();
    await Permission.locationWhenInUse.request();
    await _refresh();
    if (_camera?.isGranted == true && _location?.isGranted == true) {
      // Pressing "Allow and create key" is the person's decision to set this phone up again.
      await ref.read(servicesProvider).tokens.setRevokedHere(false);
      ref.invalidate(deviceProvider);
      try {
        await ref.read(deviceProvider.future);
      } catch (e) {
        _keyError = ApiError.from(e).message;
      }
    }
    if (!mounted) return;
    setState(() => _busy = false);
    if (await captureReady(ref) && mounted) Navigator.of(context).pop(true);
  }

  Widget _row(String title, String detail, bool ok) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(ok ? Icons.check_circle : Icons.radio_button_unchecked,
            color: ok ? IbhColors.okFg : IbhColors.muted),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(detail),
        trailing: StatusChip(ok ? 'Ready' : 'Needed', tone: ok ? ChipTone.ok : ChipTone.warn),
      );

  @override
  Widget build(BuildContext context) {
    final cam = _camera?.isGranted == true;
    final loc = _location?.isGranted == true;
    final denied = _camera?.isPermanentlyDenied == true || _location?.isPermanentlyDenied == true;
    final device = ref.watch(deviceProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Set up this phone')),
      body: ListView(padding: const EdgeInsets.all(IbhSpace.s16), children: [
        const Text(
            'To prove what you see on site, iBackHome needs the camera and your location, and a signing key '
            'that stays inside this phone.',
            style: IbhText.body),
        const SizedBox(height: IbhSpace.s16),
        _row('Camera', 'Photos and video are taken in the app only. There is no gallery upload.', cam),
        _row('Location', 'Stamps each capture with where you were.', loc),
        if (!_gps) const Alert('Location services are off. Turn on GPS in the phone settings.', tone: ChipTone.bad),
        _row('Signing key', 'Created in the Android Keystore. It never leaves this phone.', device.hasValue),
        if (_keyError != null || (device.hasError && cam && loc))
          Alert('The key could not be registered. ${_keyError ?? ApiError.from(device.error!).message}',
              tone: ChipTone.bad),
        if (denied)
          const Alert('A permission was turned off for good. Open the phone settings for iBackHome and allow it.',
              tone: ChipTone.bad),
        const SizedBox(height: IbhSpace.s24),
        FilledButton(
          onPressed: _busy ? null : _allow,
          child: _busy
              ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : const Text('Allow and create key'),
        ),
        if (denied) ...[
          const SizedBox(height: IbhSpace.s8),
          OutlinedButton(onPressed: openAppSettings, child: const Text('Open phone settings')),
        ],
      ]),
    );
  }
}
