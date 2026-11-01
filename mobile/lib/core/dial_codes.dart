/// Calling codes for the sign-in phone field. Nigeria first, then the countries Nigerians abroad
/// mostly live in. The server also accepts any `+` number typed in full, so this list is a
/// convenience, not a limit.
class DialCode {
  const DialCode(this.iso, this.name, this.dial);
  final String iso;
  final String name;
  final String dial;

  String get short => '$iso +$dial';
}

const dialCodes = <DialCode>[
  DialCode('NG', 'Nigeria', '234'),
  DialCode('GB', 'United Kingdom', '44'),
  DialCode('US', 'United States', '1'),
  DialCode('CA', 'Canada', '1'),
  DialCode('IE', 'Ireland', '353'),
  DialCode('DE', 'Germany', '49'),
  DialCode('FR', 'France', '33'),
  DialCode('NL', 'Netherlands', '31'),
  DialCode('IT', 'Italy', '39'),
  DialCode('ES', 'Spain', '34'),
  DialCode('SE', 'Sweden', '46'),
  DialCode('NO', 'Norway', '47'),
  DialCode('AE', 'United Arab Emirates', '971'),
  DialCode('SA', 'Saudi Arabia', '966'),
  DialCode('QA', 'Qatar', '974'),
  DialCode('ZA', 'South Africa', '27'),
  DialCode('GH', 'Ghana', '233'),
  DialCode('KE', 'Kenya', '254'),
  DialCode('AU', 'Australia', '61'),
  DialCode('NZ', 'New Zealand', '64'),
  DialCode('IN', 'India', '91'),
  DialCode('SG', 'Singapore', '65'),
];

/// What the server gets for a number typed beside a country code. A Nigerian number may keep its
/// leading 0 (the server reads `0803...` as `+234803...`); for any other country the leading 0 of a
/// national number is dropped and the code added: `07700 900 482` + GB -> `+447700900482`.
/// A number that already starts with `+` is sent as typed.
String composePhone(DialCode country, String typed) {
  final t = typed.trim();
  if (t.startsWith('+')) return '+${t.substring(1).replaceAll(RegExp(r'[^0-9]'), '')}';
  final digits = t.replaceAll(RegExp(r'[^0-9]'), '');
  if (country.iso == 'NG') return digits;
  final national = digits.startsWith('0') ? digits.substring(1) : digits;
  return '+${country.dial}$national';
}

/// `+44 7700 ••• 482` for "We sent a code to ..." (first four and last three digits only).
String maskIdentifier(String identifier) {
  if (identifier.contains('@')) {
    final at = identifier.indexOf('@');
    final name = identifier.substring(0, at);
    return '${name.isEmpty ? '' : name[0]}•••${identifier.substring(at)}';
  }
  final d = identifier.replaceAll(RegExp(r'[^0-9+]'), '');
  if (d.length <= 8) return identifier;
  return '${d.substring(0, d.length - 7)} ••• ${d.substring(d.length - 3)}';
}
