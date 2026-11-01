// Money is whole minor units (kobo) from the API; it is never turned into a floating-point number.

/// `₦5,433,000` for 543300000 kobo, `₦1,250.50` with kobo. Other currencies show their ISO code first.
String formatMoney(int minor, {String currency = 'NGN'}) {
  final negative = minor < 0;
  final abs = minor.abs();
  final major = (abs ~/ 100).toString();
  final kobo = abs % 100;
  final grouped = StringBuffer();
  for (var i = 0; i < major.length; i++) {
    if (i > 0 && (major.length - i) % 3 == 0) grouped.write(',');
    grouped.write(major[i]);
  }
  final cents = kobo == 0 ? '' : '.${kobo.toString().padLeft(2, '0')}';
  final symbol = currency == 'NGN' ? '₦' : '$currency ';
  return '${negative ? '-' : ''}$symbol$grouped$cents';
}
