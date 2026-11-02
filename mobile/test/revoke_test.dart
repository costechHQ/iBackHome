import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/token_store.dart';

class _Store implements SecretStore {
  final Map<String, String> data = {};
  @override
  Future<String?> read(String key) async => data[key];
  @override
  Future<void> write(String key, String value) async => data[key] = value;
  @override
  Future<void> delete(String key) async => data.remove(key);
}

void main() {
  test('a phone revoked on purpose stays revoked until it is set up again', () async {
    final tokens = TokenStore(_Store());
    expect(await tokens.revokedHere(), isFalse);
    await tokens.setRevokedHere(true);
    expect(await tokens.revokedHere(), isTrue);
    await tokens.setRevokedHere(false);
    expect(await tokens.revokedHere(), isFalse);
  });
}
