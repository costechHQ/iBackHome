import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/orders.dart';

void main() {
  group('quantities are exact, never floating point', () {
    test('plain decimals parse to whole thousandths', () {
      expect(parseMilli('120'), 120000);
      expect(parseMilli('2.5'), 2500);
      expect(parseMilli('2.05'), 2050);
      expect(parseMilli('0.001'), 1);
      expect(parseMilli(' 7 '), 7000);
    });

    test('anything else is not a quantity', () {
      for (final bad in ['', '.', '2.', '.5', '2.5555', '-1', '1e3', 'abc', '1,000', '2.5.1', '1234567890']) {
        expect(parseMilli(bad), isNull, reason: bad);
      }
    });

    test('they print without trailing zeros', () {
      expect(milliText(120000), '120');
      expect(milliText(2500), '2.5');
      expect(milliText(2050), '2.05');
      expect(milliText(1), '0.001');
      expect(milliText(0), '0');
    });

    test('what is typed comes back unchanged', () {
      for (final q in ['1', '120', '2.5', '2.05', '0.001', '99999.999']) {
        expect(milliText(parseMilli(q)!), q);
      }
    });

    test('a quantity is whole only when it has no fraction', () {
      expect(isWhole(parseMilli('140')!), isTrue);
      expect(isWhole(parseMilli('2.5')!), isFalse);
    });

    test('a quantity reads with its unit, plural unless it is one', () {
      expect(quantityLabel({'quantity': '140', 'unit': 'bag'}), '140 bags');
      expect(quantityLabel({'quantity': '1', 'unit': 'roll'}), '1 roll');
      expect(quantityLabel({'quantity': '2.50', 'unit': 'tonne'}), '2.5 tonnes');
    });
  });

  group('how an order reads', () {
    test('the short reference comes from the id', () {
      expect(orderRef('0141abcd-1111-2222-3333-444444444444'), 'O-0141');
      expect(orderRef('ab'), 'O-AB');
    });

    test('the supplier is named, with a fallback', () {
      expect(supplierName({'supplier': {'id': 's', 'name': ' Ugwu Materials '}}), 'Ugwu Materials');
      expect(supplierName({'supplier': {'id': 's', 'name': ''}}), 'Supplier');
      expect(supplierName({}), 'Supplier');
    });

    test('the items are summarised', () {
      Map<String, dynamic> order(List<String> items) => {'items': [for (final i in items) {'item': i}]};
      expect(itemsSummary(order([])), 'No items');
      expect(itemsSummary(order(['Cement'])), 'Cement');
      expect(itemsSummary(order(['Cement', 'Sand', 'Mesh'])), 'Cement +2 more');
    });
  });
}
