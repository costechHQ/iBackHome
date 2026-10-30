import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:uuid/uuid.dart';

/// Tokens and the install id, in Keystore-backed encrypted storage.
class TokenStore {
  TokenStore([FlutterSecureStorage? storage]) : _s = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _s;
  String? _access;

  String? get accessToken => _access;

  Future<void> load() async => _access = await _s.read(key: 'access');

  Future<String?> refreshToken() => _s.read(key: 'refresh');

  Future<void> save(String access, String refresh) async {
    _access = access;
    await _s.write(key: 'access', value: access);
    await _s.write(key: 'refresh', value: refresh);
  }

  Future<void> clear() async {
    _access = null;
    await _s.delete(key: 'access');
    await _s.delete(key: 'refresh');
  }

  /// Forget the install id (after the device key was revoked): a new one is made next time.
  Future<void> resetDeviceId() => _s.delete(key: 'device_id');

  /// A stable id for this install; sent as `X-Device-Id` and used to register the signing key.
  Future<String> deviceId() async {
    var id = await _s.read(key: 'device_id');
    if (id == null) {
      id = 'android-${const Uuid().v4()}';
      await _s.write(key: 'device_id', value: id);
    }
    return id;
  }
}
