// Helpers for material orders as `GET /projects/{id}/orders` returns them (MX-05).
//
// Quantities are decimal strings with up to three places ("120", "2.5"). They are held here as whole
// thousandths (int) and never as floating-point numbers, so a count the supervisor makes matches the
// ordered quantity exactly, which is what the server requires.

/// A short reference to read aloud, from the id: `O-1A2B`. Orders have no human reference yet.
String orderRef(Object? id) {
  final text = '$id'.replaceAll('-', '');
  return 'O-${text.substring(0, text.length < 4 ? text.length : 4).toUpperCase()}';
}

/// The supplier's name, or a plain fallback.
String supplierName(Map<String, dynamic> order) {
  final s = order['supplier'];
  final name = s is Map ? (s['name'] as String?)?.trim() : null;
  return name == null || name.isEmpty ? 'Supplier' : name;
}

/// The order's lines: `{item, unit, quantity, unit_price_minor}`.
List<Map<String, dynamic>> orderLines(Map<String, dynamic> order) => (order['items'] as List).cast<Map<String, dynamic>>();

/// "Cement, 50 kg bag", or "Cement, 50 kg bag +2 more".
String itemsSummary(Map<String, dynamic> order) {
  final lines = orderLines(order);
  if (lines.isEmpty) return 'No items';
  return lines.length == 1 ? '${lines.first['item']}' : '${lines.first['item']} +${lines.length - 1} more';
}

/// "120" -> 120000, "2.5" -> 2500. Null for anything that is not a plain decimal of at most three places.
int? parseMilli(String text) {
  final m = RegExp(r'^(\d{1,9})(?:\.(\d{1,3}))?$').firstMatch(text.trim());
  if (m == null) return null;
  final whole = int.parse(m.group(1)!);
  final fraction = (m.group(2) ?? '').padRight(3, '0');
  return whole * 1000 + int.parse(fraction);
}

/// 120000 -> "120", 2500 -> "2.5", 2050 -> "2.05".
String milliText(int milli) {
  final whole = milli ~/ 1000;
  final fraction = (milli % 1000).toString().padLeft(3, '0').replaceFirst(RegExp(r'0+$'), '');
  return fraction.isEmpty ? '$whole' : '$whole.$fraction';
}

bool isWhole(int milli) => milli % 1000 == 0;

/// "140 bags", "2.5 tonnes", "1 roll".
String quantityLabel(Map<String, dynamic> line) {
  final milli = parseMilli('${line['quantity']}');
  final text = milli == null ? '${line['quantity']}' : milliText(milli);
  final unit = '${line['unit']}';
  return '$text $unit${text == '1' ? '' : 's'}';
}
