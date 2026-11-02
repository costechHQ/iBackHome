import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api.dart';
import 'api_error.dart';
import 'capture_service.dart';
import 'config.dart';
import 'push.dart';
import 'queue_db.dart';
import 'signing.dart';
import 'sync_service.dart';
import 'token_store.dart';

/// Everything the screens share, built once in `main()`.
class Services {
  Services._(this.tokens, this.api, this.db, this.keystore, this.sync, this.capture, this.signedOut, {this.saveReads = true});

  /// Whether [cachedGet] saves what it reads. Always on in the app; widget tests turn it off because a
  /// real database write inside a fake clock leaves SQLite's lock timer pending.
  final bool saveReads;

  final TokenStore tokens;
  final Api api;
  final QueueDb db;
  final Keystore keystore;
  final SyncService sync;
  final CaptureService capture;

  /// Bumped when the server refuses our refresh token (the session is over).
  final ValueNotifier<int> signedOut;

  @visibleForTesting
  factory Services.forTesting({
    required TokenStore tokens,
    required Api api,
    required QueueDb db,
    Keystore? keystore,
    ValueNotifier<int>? signedOut,
    bool saveReads = false,
  }) {
    final ks = keystore ?? Keystore(Config.keyAlias);
    return Services._(tokens, api, db, ks, SyncService(api, db), CaptureService(db, ks), signedOut ?? ValueNotifier<int>(0),
        saveReads: saveReads);
  }

  static Future<Services> create() async {
    final tokens = TokenStore();
    await tokens.load();
    final signedOut = ValueNotifier<int>(0);
    final api = Api(tokens, onSignedOut: () => signedOut.value++);
    final db = await QueueDb.open();
    final keystore = Keystore(Config.keyAlias);
    return Services._(tokens, api, db, keystore, SyncService(api, db), CaptureService(db, keystore), signedOut);
  }

  /// Set while the screens are showing a saved answer because there is no signal; it holds when that
  /// answer was saved. Cleared by the next read that reaches the server.
  final ValueNotifier<DateTime?> staleSince = ValueNotifier<DateTime?>(null);

  /// A read that is remembered on the phone. If the server answers, that answer is saved and
  /// returned. If only the connection fails, the last saved answer is returned and [staleSince] is
  /// set. Every other error (401, 403 after a rotation, 404, 5xx) is rethrown, so a revoked person
  /// never sees stale access.
  Future<T> cachedGet<T>(String path, {Map<String, dynamic>? query}) async {
    final key = query == null || query.isEmpty ? path : '$path?${query.entries.map((e) => '${e.key}=${e.value}').join('&')}';
    try {
      final data = await api.get<T>(path, query: query);
      staleSince.value = null;
      if (saveReads) unawaited(_remember(key, data));
      return data;
    } on ApiError catch (e) {
      if (!e.isNetwork) rethrow;
      final hit = saveReads ? await db.getCache(key) : null;
      if (hit == null) rethrow;
      final current = staleSince.value;
      if (current == null || hit.savedAt.isBefore(current)) staleSince.value = hit.savedAt;
      return jsonDecode(hit.body) as T;
    }
  }

  /// Saving a copy must never break the screen that asked for the data.
  Future<void> _remember(String key, Object? data) async {
    try {
      await db.putCache(key, jsonEncode(data));
    } catch (_) {}
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
    if (await tokens.revokedHere()) {
      throw ApiError('device_revoked_here',
          'You revoked this phone, so it cannot capture evidence. Set it up again to create a new signing key.');
    }
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
    await tokens.markDeviceRegistered();
    return deviceId;
  }

  /// This person's registered phones (`GET /devices`), newest first, including revoked ones. Read live
  /// and never saved: a security list must not be shown from an old copy.
  Future<List<Map<String, dynamic>>> listDevices() async {
    final rows = await api.get<List<dynamic>>('/devices');
    return rows.cast<Map<String, dynamic>>();
  }

  /// Revokes another phone of this person (an old or lost one). This phone's own key is untouched.
  Future<void> revokeOtherDevice(String pk) async {
    await api.post<Map<String, dynamic>>('/devices/$pk/revoke', idempotencyKey: 'revoke-$pk');
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
    await tokens.setRevokedHere(true);
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
    if (_s.saveReads) await _s.db.clearCache(); // a new sign-in never starts from someone else's saved lists
    await _loadMe();
  }

  /// `/me` is remembered too: opened without signal, the app still knows the role and shows the saved projects.
  Future<void> _loadMe() async {
    final me = await _s.cachedGet<Map<String, dynamic>>('/me');
    state = AuthState(AuthStatus.signedIn, me: me);
  }

  Future<void> agreeToTerms() async {
    final c = await _s.api.get<Map<String, dynamic>>('/me/consent');
    await _s.api.post<Map<String, dynamic>>('/me/consent',
        body: {'terms_version': c['terms_version'], 'privacy_version': c['privacy_version']});
    await _loadMe();
  }

  /// Saves the person's own name (PATCH /me) and keeps the server's answer. Phone and email are sign-in
  /// identifiers and are not changed here; time is always Nigerian time for these roles.
  Future<void> updateProfile({required String fullName}) async {
    final me = await _s.api.patch<Map<String, dynamic>>('/me', body: {'full_name': fullName});
    if (_s.saveReads) await _s.db.putCache('/me', jsonEncode(me));
    state = AuthState(AuthStatus.signedIn, me: me);
  }

  Future<void> signOut() async {
    // Forget this phone's push token while the session still works, so the next person never gets these alerts.
    await ref.read(pushProvider).stop();
    await _s.tokens.clear();
    if (_s.saveReads) await _s.db.clearCache();
    state = const AuthState(AuthStatus.signedOut);
  }
}

final authProvider = NotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);
