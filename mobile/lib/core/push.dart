import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_error.dart';
import 'services.dart';

/// A push as the app sees it: only the ids the server puts in the data payload (no names or amounts).
class PushMessage {
  const PushMessage(this.data, {this.title, this.body});
  final Map<String, String> data;
  final String? title;
  final String? body;
}

/// The phone-side push layer (Firebase Messaging). A fake replaces it in tests; without
/// `google-services.json` [start] returns false and push stays off.
abstract class PushBackend {
  /// Starts Firebase and asks for permission. False when push cannot work here (no Firebase project in the
  /// build, permission refused).
  Future<bool> start();
  Future<String?> token();
  Stream<String> get tokenRefreshed;
  Stream<PushMessage> get foreground;
  Stream<PushMessage> get opened;
  Future<PushMessage?> launchedBy();
  Future<void> deleteToken();
}

class FirebasePushBackend implements PushBackend {
  FirebaseMessaging? _m;

  static PushMessage _of(RemoteMessage m) => PushMessage(
        {for (final e in m.data.entries) e.key: '${e.value}'},
        title: m.notification?.title,
        body: m.notification?.body,
      );

  @override
  Future<bool> start() async {
    try {
      await Firebase.initializeApp();
    } catch (_) {
      return false; // no google-services.json in this build
    }
    final m = _m = FirebaseMessaging.instance;
    final settings = await m.requestPermission();
    return settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional;
  }

  @override
  Future<String?> token() async => _m?.getToken();

  @override
  Stream<String> get tokenRefreshed => _m?.onTokenRefresh ?? const Stream.empty();

  @override
  Stream<PushMessage> get foreground => _m == null ? const Stream.empty() : FirebaseMessaging.onMessage.map(_of);

  @override
  Stream<PushMessage> get opened => _m == null ? const Stream.empty() : FirebaseMessaging.onMessageOpenedApp.map(_of);

  @override
  Future<PushMessage?> launchedBy() async {
    final m = await _m?.getInitialMessage();
    return m == null ? null : _of(m);
  }

  @override
  Future<void> deleteToken() async {
    try {
      await _m?.deleteToken();
    } catch (_) {}
  }
}

/// Registers this phone's push token with the server while someone is signed in, forgets it on sign-out,
/// and hands "a push was opened / arrived" to the app. Push is a convenience: every failure here is
/// swallowed, never shown, and the app works the same without it.
class PushService {
  PushService(this._s, this._backend);

  final Services _s;
  final PushBackend _backend;

  final _opened = StreamController<PushMessage>.broadcast();
  final _arrived = StreamController<PushMessage>.broadcast();
  final List<StreamSubscription<Object?>> _subs = [];
  bool _on = false;
  String? _registered;

  /// A push the person tapped (also the one that launched the app).
  Stream<PushMessage> get opened => _opened.stream;

  /// A push that arrived while the app was open.
  Stream<PushMessage> get arrived => _arrived.stream;

  @visibleForTesting
  String? get registeredToken => _registered;

  /// Called after sign-in. Needs the phone's registered device id, which [Services.registerDevice] sets.
  Future<void> start() async {
    if (_on) return;
    try {
      if (!await _backend.start()) return;
      _on = true;
      _subs
        ..add(_backend.tokenRefreshed.listen((t) => unawaited(_register(t))))
        ..add(_backend.foreground.listen(_arrived.add))
        ..add(_backend.opened.listen(_opened.add));
      final t = await _backend.token();
      if (t != null) await _register(t);
      final first = await _backend.launchedBy();
      if (first != null) _opened.add(first);
    } catch (_) {
      _on = false;
    }
  }

  Future<void> _register(String token) async {
    if (token == _registered) return;
    try {
      var pk = _s.device?['id'] as String?;
      if (pk == null) {
        await _s.registerDevice();
        pk = _s.device?['id'] as String?;
      }
      if (pk == null) return;
      await _s.api.post<Map<String, dynamic>>('/me/push-tokens', body: {'device_pk': pk, 'token': token});
      _registered = token;
    } on ApiError {
      // Offline or refused: the next token refresh or launch tries again.
    }
  }

  /// On sign-out: tell the server to forget this phone's token, then drop it, so a pushed alert is never
  /// delivered to the next person using the phone. Must run while the session is still valid.
  Future<void> stop() async {
    final pk = _s.device?['id'] as String?;
    for (final s in _subs) {
      await s.cancel();
    }
    _subs.clear();
    if (!_on) return;
    _on = false;
    _registered = null;
    try {
      if (pk != null) await _s.api.delete('/me/push-tokens/$pk');
    } catch (_) {}
    await _backend.deleteToken();
  }
}

final pushBackendProvider = Provider<PushBackend>((_) => FirebasePushBackend());

final pushProvider = Provider<PushService>((ref) {
  final s = PushService(ref.read(servicesProvider), ref.read(pushBackendProvider));
  ref.onDispose(s.stop);
  return s;
});
