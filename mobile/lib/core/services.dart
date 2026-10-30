import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api.dart';
import 'api_error.dart';
import 'capture_service.dart';
import 'config.dart';
import 'queue_db.dart';
import 'signing.dart';
import 'sync_service.dart';
import 'token_store.dart';

/// Everything the screens share, built once in `main()`.
class Services {
  Services._(this.tokens, this.api, this.db, this.keystore, this.sync, this.capture, this.signedOut);

  final TokenStore tokens;
  final Api api;
  final QueueDb db;
  final Keystore keystore;
  final SyncService sync;
  final CaptureService capture;

  /// Bumped when the server refuses our refresh token (the session is over).
  final ValueNotifier<int> signedOut;

  static Future<Services> create() async {
    final tokens = TokenStore();
    await tokens.load();
    final signedOut = ValueNotifier<int>(0);
    final api = Api(tokens, onSignedOut: () => signedOut.value++);
    final db = await QueueDb.open();
    final keystore = Keystore(Config.keyAlias);
    return Services._(tokens, api, db, keystore, SyncService(api, db), CaptureService(db, keystore), signedOut);
  }

  /// Sends a write now; if there is no signal, keeps it on the phone and sends it later with the
  /// same `Idempotency-Key`. Returns true when the server already has it.
  Future<bool> sendOrQueue({
    required String kind,
    required String path,
    Map<String, dynamic>? body,
    required String label,
    String? projectId,
  }) async {
    final id = Api.newKey();
    try {
      await api.post<Map<String, dynamic>>(path, body: body, idempotencyKey: id);
      return true;
    } on ApiError catch (e) {
      if (!e.isNetwork) rethrow;
      await queueAction(id: id, kind: kind, path: path, body: body, label: label, projectId: projectId);
      return false;
    }
  }

  Future<void> queueAction({
    String? id,
    required String kind,
    required String path,
    Map<String, dynamic>? body,
    required String label,
    String? projectId,
  }) async {
    await db.addAction(QueuedAction(
      id: id ?? Api.newKey(),
      kind: kind,
      path: path,
      body: jsonEncode(body ?? <String, dynamic>{}),
      label: label,
      projectId: projectId,
    ));
    unawaited(sync.syncNow());
  }

  /// The server's record of this phone's key (its row id is needed to revoke it).
  Map<String, dynamic>? device;

  /// Registers this install's public key (idempotent: the same device answers 200).
  /// Needed before any capture. Returns the device id the server knows.
  ///
  /// If operations revoked the key, this throws `device_revoked`: the app stops capturing.
  Future<String> registerDevice() async {
    final deviceId = await tokens.deviceId();
    final publicKey = await keystore.ensureKey();
    final record = await api.post<Map<String, dynamic>>(
      '/devices',
      body: {'device_id': deviceId, 'public_key': publicKey},
      idempotencyKey: 'device-$deviceId',
    );
    if (record['revoked_at'] != null) {
      throw ApiError('device_revoked',
          'This phone\'s signing key was revoked, so it can no longer capture evidence. Contact operations.');
    }
    device = record;
    return deviceId;
  }

  /// Revokes this phone's key on the server, deletes it from the Keystore and forgets the device
  /// id, so a new key is made next time. Captures already queued with the old key will be
  /// rejected by the server: say so before calling.
  Future<void> revokeThisPhone() async {
    final pk = device?['id'] as String?;
    if (pk == null) throw ApiError('device_unknown', 'This phone is not registered yet.');
    await api.post<Map<String, dynamic>>('/devices/$pk/revoke', idempotencyKey: 'revoke-$pk');
    await keystore.deleteKey();
    await tokens.resetDeviceId();
    device = null;
  }
}

final servicesProvider = Provider<Services>((_) => throw UnimplementedError('override in main()'));

enum AuthStatus { unknown, signedOut, signedIn }

class AuthState {
  const AuthState(this.status, {this.me, this.sessionExpired = false});
  final AuthStatus status;
  final Map<String, dynamic>? me;

  /// True when the server ended the session (not when the user signed out): the sign-in screen
  /// then tells the user their queued captures are safe.
  final bool sessionExpired;

  String? get role => me?['role'] as String?;
  bool get isSupervisor => role == 'supervisor';
  bool get isContractor => role == 'contractor';
}

/// Roles this app serves; clients, suppliers and ops use the web app.
const appRoles = {'supervisor', 'contractor'};

class AuthNotifier extends Notifier<AuthState> {
  late final Services _s = ref.read(servicesProvider);

  @override
  AuthState build() {
    _s.signedOut.addListener(_onSignedOut);
    ref.onDispose(() => _s.signedOut.removeListener(_onSignedOut));
    return const AuthState(AuthStatus.unknown);
  }

  void _onSignedOut() => state = const AuthState(AuthStatus.signedOut, sessionExpired: true);

  /// On launch: use the saved session if there is one.
  Future<void> restore() async {
    if (_s.tokens.accessToken == null && await _s.tokens.refreshToken() == null) {
      state = const AuthState(AuthStatus.signedOut);
      return;
    }
    try {
      await _loadMe();
    } on ApiError catch (e) {
      // Offline at launch keeps the session; the queue and cached screens still work.
      state = e.isNetwork ? const AuthState(AuthStatus.signedIn) : const AuthState(AuthStatus.signedOut);
    }
  }

  Future<void> requestCode(String identifier, String? channel) =>
      _s.api.post<Map<String, dynamic>>('/auth/otp/request',
          body: {'identifier': identifier, 'channel': ?channel});

  Future<void> verify(String identifier, String code) async {
    final pair = await _s.api.post<Map<String, dynamic>>('/auth/otp/verify',
        body: {'identifier': identifier, 'code': code});
    await _s.tokens.save(pair['access_token'] as String, pair['refresh_token'] as String);
    await _loadMe();
  }

  Future<void> _loadMe() async {
    final me = await _s.api.get<Map<String, dynamic>>('/me');
    state = AuthState(AuthStatus.signedIn, me: me);
  }

  Future<void> agreeToTerms() async {
    final c = await _s.api.get<Map<String, dynamic>>('/me/consent');
    await _s.api.post<Map<String, dynamic>>('/me/consent',
        body: {'terms_version': c['terms_version'], 'privacy_version': c['privacy_version']});
    await _loadMe();
  }

  Future<void> signOut() async {
    await _s.tokens.clear();
    state = const AuthState(AuthStatus.signedOut);
  }
}

final authProvider = NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
