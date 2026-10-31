import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

/// Where secrets live. In the app this is Keystore-backed encrypted storage; tests use memory.
abstract class SecretStore {
  Future<String?> read(String key);
  Future<void> write(String key, String value);
  Future<void> delete(String key);
}

class SecureSecretStore implements SecretStore {
  const SecureSecretStore([this._s = const FlutterSecureStorage()]);
  final FlutterSecureStorage _s;

  @override
  Future<String?> read(String key) => _s.read(key: key);
  @override
  Future<void> write(String key, String value) => _s.write(key: key, value: value);
  @override
  Future<void> delete(String key) => _s.delete(key: key);
}

/// Tokens and the install id.
class TokenStore {
  TokenStore([SecretStore? store]) : _s = store ?? const SecureSecretStore();

  final SecretStore _s;
  String? _access;

  String? get accessToken => _access;

  Future<void> load() async => _access = await _s.read('access');

  Future<String?> refreshToken() => _s.read('refresh');

  Future<void> save(String access, String refresh) async {
    _access = access;
    await _s.write('access', access);
    await _s.write('refresh', refresh);
  }

  Future<void> clear() async {
    _access = null;
    await _s.delete('access');
    await _s.delete('refresh');
  }

  /// Forget the install id (after the device key was revoked): a new one is made next time.
  Future<void> resetDeviceId() => _s.delete('device_id');

  /// True after the person revoked this phone on purpose: it stays unregistered until they set it up again.
  Future<bool> revokedHere() async => await _s.read('revoked_here') == '1';

  Future<void> setRevokedHere(bool v) => v ? _s.write('revoked_here', '1') : _s.delete('revoked_here');

  /// A stable id for this install; sent as `X-Device-Id` and used to register the signing key.
  Future<String> deviceId() async {
    var id = await _s.read('device_id');
    if (id == null) {
      id = 'android-${const Uuid().v4()}';
      await _s.write('device_id', id);
    }
    return id;
  }
}
