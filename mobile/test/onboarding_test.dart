import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/dial_codes.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/payout_screen.dart';
import 'package:ibackhome_mobile/features/vetting_screen.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

class _Store implements SecretStore {
  final Map<String, String> data = {};
  @override
  Future<String?> read(String key) async => data[key];
  @override
  Future<void> write(String key, String value) async => data[key] = value;
  @override
  Future<void> delete(String key) async => data.remove(key);
}

class _Server implements HttpClientAdapter {
  _Server(this.routes);
  final Map<String, (int, Object)> routes;
  final List<RequestOptions> seen = [];

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? body, Future<void>? cancel) async {
    seen.add(options);
    final hit = routes['${options.method} ${options.path}'] ?? (404, {'error': {'code': 'not_found', 'message': 'No.'}});
    return ResponseBody.fromString(jsonEncode(hit.$2), hit.$1, headers: {
      Headers.contentTypeHeader: ['application/json'],
    });
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  group('phone numbers', () {
    final ng = dialCodes.firstWhere((c) => c.iso == 'NG');
    final gb = dialCodes.firstWhere((c) => c.iso == 'GB');

    test('a Nigerian number is sent as typed, the server reads 0803... itself', () {
      expect(composePhone(ng, '0803 000 0002'), '08030000002');
    });

    test('another country drops the national leading 0 and adds its code', () {
      expect(composePhone(gb, '07700 900 482'), '+447700900482');
    });

    test('a number typed with + is sent as typed', () {
      expect(composePhone(gb, '+234 803 000 0002'), '+2348030000002');
    });

    test('the code screen never shows the whole number', () {
      expect(maskIdentifier('+447700900482'), '+44770 ••• 482');
      expect(maskIdentifier('chidi@example.com'), 'c•••@example.com');
    });
  });

  group('screens against a fake server', () {
    late Directory tmp;
    late QueueDb db;

    setUp(() async {
      tmp = await Directory.systemTemp.createTemp('ibh_onb');
      db = await QueueDb.open(path: '${tmp.path}/q.db');
    });

    tearDown(() async {
      await db.close();
      await tmp.delete(recursive: true);
    });

    Future<(_Server, Widget)> host(Map<String, (int, Object)> routes, Widget child) async {
      final server = _Server(routes);
      final tokens = TokenStore(_Store());
      final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
      final services = Services.forTesting(tokens: tokens, api: api, db: db);
      return (
        server,
        ProviderScope(overrides: [servicesProvider.overrideWithValue(services)], child: MaterialApp(home: child))
      );
    }

    Future<void> tapText(WidgetTester t, String text) async {
      await t.ensureVisible(find.text(text).first);
      await t.tap(find.text(text).first);
      await t.pumpAndSettle();
    }

    testWidgets('the supervisor application walks five steps and sends what was typed', (tester) async {
      final (server, widget) = await host({
        'PUT /supervisors/me/profile': (200, {'vetting_status': 'pending'}),
      }, const ApplicationFlow());
      await tester.pumpWidget(widget);
      expect(find.text('Apply to supervise sites across Nigeria'), findsOneWidget);
      await tapText(tester, 'Start');

      // 1 Registration: Continue stays off until a number is typed.
      expect(find.text('1 of 5'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Continue')).onPressed, isNull);
      await tester.enterText(find.byType(TextField).first, 'R.24816');
      await tester.pump();
      await tapText(tester, 'Continue');

      // 2 NIN: 11 digits, hidden as typed; Continue stays off until all 11 are in.
      expect(find.text('Your NIN'), findsOneWidget);
      expect(find.text('11 digits. Hidden as you type.'), findsOneWidget);
      expect(find.textContaining('Never shown to clients or contractors'), findsOneWidget);
      expect(tester.widget<TextField>(find.byType(TextField)).obscureText, isTrue);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Continue')).onPressed, isNull);
      await tester.enterText(find.byType(TextField), '1234567890'); // ten digits is not a NIN
      await tester.pump();
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Continue')).onPressed, isNull);
      await tester.enterText(find.byType(TextField), '12345678901');
      await tester.pump();
      await tapText(tester, 'Continue');

      // 3 Guarantors
      for (var i = 0; i < 2; i++) {
        await tester.enterText(find.byType(TextField).at(i * 2), i == 0 ? 'Ngozi Eze' : 'Emeka Ani');
        await tester.enterText(find.byType(TextField).at(i * 2 + 1), i == 0 ? '+2348055550114' : '+2348055550115');
        await tester.pump();
        await tester.ensureVisible(find.byType(DropdownButtonFormField<String>).at(i));
        await tester.tap(find.byType(DropdownButtonFormField<String>).at(i));
        await tester.pumpAndSettle();
        await tester.tap(find.text(i == 0 ? 'Former employer' : 'Colleague').last);
        await tester.pumpAndSettle();
      }
      await tapText(tester, 'Continue');

      // 4 Relatives: No
      await tapText(tester, 'No');
      await tapText(tester, 'Continue');

      // 5 Review, then submit
      expect(find.text('COREN · R.24816'), findsOneWidget);
      expect(find.text('Ngozi Eze · Emeka Ani'), findsOneWidget);
      // Even here only the last four digits show.
      expect(find.text('NIN · •••••••8901'), findsOneWidget);
      expect(find.textContaining('12345678901'), findsNothing);
      await tapText(tester, 'Submit application');

      final put = server.seen.singleWhere((r) => r.method == 'PUT');
      expect(put.data, {
        'registration_body': 'COREN',
        'registration_no': 'R.24816',
        'nin': '12345678901',
        'guarantor_1': 'Ngozi Eze, +2348055550114, Former employer',
        'guarantor_2': 'Emeka Ani, +2348055550115, Colleague',
        'related_contractors': <Object>[],
      });
      expect(put.headers['Idempotency-Key'], isNotEmpty);
    });

    testWidgets('if the server cannot take a NIN right now, the review step says so and keeps the application', (tester) async {
      final (_, widget) = await host({
        'PUT /supervisors/me/profile': (503, {'error': {'code': 'nin_not_configured', 'message': 'We can\'t take a NIN right now. Please try again later.'}}),
      }, const ApplicationFlow(startAtForm: true, registrationNo: 'R.1'));
      await tester.pumpWidget(widget);
      await tapText(tester, 'Continue'); // registration -> NIN
      await tester.enterText(find.byType(TextField), '12345678901');
      await tester.pump();
      await tapText(tester, 'Continue'); // NIN -> guarantors
      for (var i = 0; i < 2; i++) {
        await tester.enterText(find.byType(TextField).at(i * 2), i == 0 ? 'Ngozi Eze' : 'Emeka Ani');
        await tester.enterText(find.byType(TextField).at(i * 2 + 1), '+2348055550114');
        await tester.pump();
        await tester.ensureVisible(find.byType(DropdownButtonFormField<String>).at(i));
        await tester.tap(find.byType(DropdownButtonFormField<String>).at(i));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Colleague').last);
        await tester.pumpAndSettle();
      }
      await tapText(tester, 'Continue');
      await tapText(tester, 'No');
      await tapText(tester, 'Continue');
      await tapText(tester, 'Submit application');
      expect(find.textContaining('can\'t take a NIN right now'), findsOneWidget);
      expect(find.text('Submit application'), findsOneWidget); // still here, to try again
    });

    testWidgets('the NIN field takes digits only, at most 11, and can be shown or hidden', (tester) async {
      final (_, widget) = await host({}, const ApplicationFlow(startAtForm: true, registrationNo: 'R.1'));
      await tester.pumpWidget(widget);
      await tapText(tester, 'Continue'); // registration -> NIN

      await tester.enterText(find.byType(TextField), '12ab-34 5678901234567');
      await tester.pump();
      final field = tester.widget<TextField>(find.byType(TextField));
      expect(field.controller!.text, '12345678901'); // letters and spaces dropped, cut at 11

      expect(field.obscureText, isTrue);
      await tester.tap(find.byTooltip('Show NIN'));
      await tester.pump();
      expect(tester.widget<TextField>(find.byType(TextField)).obscureText, isFalse);
      await tester.tap(find.byTooltip('Hide NIN'));
      await tester.pump();
      expect(tester.widget<TextField>(find.byType(TextField)).obscureText, isTrue);
    });

    testWidgets('the NIN field turns off suggestions and autofill, since it is personal data', (tester) async {
      final (_, widget) = await host({}, const ApplicationFlow(startAtForm: true, registrationNo: 'R.1'));
      await tester.pumpWidget(widget);
      await tapText(tester, 'Continue');
      final field = tester.widget<TextField>(find.byType(TextField));
      expect(field.enableSuggestions, isFalse);
      expect(field.autocorrect, isFalse);
    });

    testWidgets('payout: a found account shows the bank\'s name and enables Save', (tester) async {
      final (server, widget) = await host({
        'GET /banks': (200, [
          {'code': '011', 'name': 'First Bank of Nigeria'},
          {'code': '058', 'name': 'GTBank'},
        ]),
        'GET /me/payout/recipient': (404, {'error': {'code': 'no_payout_recipient', 'message': 'None.'}}),
        'POST /me/payout/recipient/resolve': (200, {'account_name': 'OBINNA OBI'}),
        'PUT /me/payout/recipient': (200, {'account_name': 'OBINNA OBI', 'bank_name': 'First Bank of Nigeria', 'account_number_masked': '******6789'}),
      }, const PayoutScreen());
      await tester.pumpWidget(widget);
      await tester.pumpAndSettle();
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Save payout account')).onPressed, isNull);

      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('First Bank of Nigeria').last);
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), '3021846789');
      await tester.pumpAndSettle();

      expect(find.text('Account found'), findsOneWidget);
      expect(find.text('OBINNA OBI'), findsOneWidget);
      await tester.tap(find.text('Save payout account'));
      await tester.pumpAndSettle();
      final put = server.seen.singleWhere((r) => r.method == 'PUT');
      expect(put.data, {'bank_code': '011', 'account_number': '3021846789'});
    });

    testWidgets('payout: an account the bank cannot find says so and cannot be saved', (tester) async {
      final (_, widget) = await host({
        'GET /banks': (200, [
          {'code': '011', 'name': 'First Bank of Nigeria'},
        ]),
        'GET /me/payout/recipient': (404, {'error': {'code': 'no_payout_recipient', 'message': 'None.'}}),
        'POST /me/payout/recipient/resolve': (422, {'error': {'code': 'account_not_found', 'message': 'No such account.'}}),
      }, const PayoutScreen());
      await tester.pumpWidget(widget);
      await tester.pumpAndSettle();
      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('First Bank of Nigeria').last);
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), '3021846798');
      await tester.pumpAndSettle();

      expect(find.text('We couldn\'t find that account'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Save payout account')).onPressed, isNull);
    });
  });
}
