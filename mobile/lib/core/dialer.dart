import 'package:url_launcher/url_launcher.dart';

/// Opens the phone's dialer with [phone] ready to call (it does not place the call by itself).
/// Returns false if no dialer could open.
Future<bool> callPhone(String phone) async {
  try {
    return await launchUrl(Uri(scheme: 'tel', path: phone), mode: LaunchMode.externalApplication);
  } catch (_) {
    return false;
  }
}
