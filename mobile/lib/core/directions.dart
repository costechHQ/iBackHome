import 'package:url_launcher/url_launcher.dart';

/// Opens the phone's maps app with directions to a point. Tries a `geo:` link first (any maps app),
/// then the Google Maps web link. Returns false if neither could open.
Future<bool> openDirections(double lat, double lon, {String? label}) async {
  final q = Uri.encodeComponent(label ?? 'Site');
  final geo = Uri.parse('geo:$lat,$lon?q=$lat,$lon($q)');
  final web = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$lat,$lon');
  for (final uri in [geo, web]) {
    try {
      if (await launchUrl(uri, mode: LaunchMode.externalApplication)) return true;
    } catch (_) {}
  }
  return false;
}
