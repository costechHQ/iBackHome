/// Build-time settings. Run against the local Docker API from the emulator with the defaults, or
/// pass `--dart-define=API_BASE_URL=https://staging.example.com/api/v1` for a real phone.
class Config {
  Config._();
  static const apiBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000/api/v1');

  /// Sample data for the screens whose backend routes do not exist yet (orders, deliveries and the
  /// alerts feed). On by default in debug builds only; a release build never shows sample data.
  /// Turn it on or off with `--dart-define=IBH_MOCKS=true|false`. See `core/mock_data.dart`.
  static const mocks = bool.fromEnvironment('IBH_MOCKS', defaultValue: !bool.fromEnvironment('dart.vm.product'));

  /// The Keystore alias of this install's signing key.
  static const keyAlias = 'ibackhome_evidence_key';
}
