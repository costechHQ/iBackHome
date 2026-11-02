import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/alerts_screen.dart';
import 'package:ibackhome_mobile/features/delivery_screen.dart';
import 'package:ibackhome_mobile/features/orders_screen.dart';
import 'package:ibackhome_mobile/features/reports_screen.dart';
import 'package:ibackhome_mobile/features/spot_checks_screen.dart';
import 'package:ibackhome_mobile/ui/markdown_lite.dart';
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

final _draftReport = {
  'id': 'r1',
  'week_start': '2027-01-04',
  'status': 'draft',
  'body_md': '## Summary\nThe supervisor sent **Plastering** back.\n- North render has cracks\n- Two items were accepted',
  'evidence_ids': ['2246aaaa-0000-0000-0000-000000000000'],
};

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  group('spot check findings', () {
    test('become one plain sentence per answer, with the reason when the work does not match', () {
      expect(
        composeSpotFindings(matches: 'partly', doesntMatch: '  Rear slope has 6 sheets missing.  ', materials: 'yes', workers: 7, captures: 6),
        'The work matches the latest claim: Partly. What doesn\'t match: Rear slope has 6 sheets missing. Materials on site match approved orders: Yes. Workers on site: 7. Captures: 6.',
      );
    });

    test('leave out the reason when the work matches, and stay long enough for the server', () {
      final text = composeSpotFindings(matches: 'yes', doesntMatch: 'ignored', materials: 'none', workers: 0, captures: 1);
      expect(text, isNot(contains('ignored')));
      expect(text, contains('No orders'));
      expect(text.length, greaterThanOrEqualTo(10)); // the API needs at least 10 characters
    });
  });

  testWidgets('the report renders headings, bullets and bold, and nothing else', (tester) async {
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: MarkdownLite(_draftReport['body_md']! as String))));
    expect(find.text('Summary'), findsOneWidget);
    expect(find.text('• '), findsNothing); // the bullet is drawn on its own, beside the text
    expect(find.textContaining('North render has cracks'), findsOneWidget);
    expect(find.textContaining('Plastering', findRichText: true), findsOneWidget);
  });

  group('screens against a fake server', () {
    late Directory tmp;
    late QueueDb db;
    late _Server server;
    late ProviderContainer container;

    setUp(() async {
      tmp = await Directory.systemTemp.createTemp('ibh_p3');
      db = await QueueDb.open(path: '${tmp.path}/q.db');
    });

    tearDown(() async {
      container.dispose();
      await db.close();
      await tmp.delete(recursive: true);
    });

    Future<Widget> host(WidgetTester tester, Map<String, (int, Object)> routes, Widget child) async {
      final w = await tester.runAsync(() async {
        server = _Server(routes);
        final tokens = TokenStore(_Store());
        await tokens.save('a', 'r' * 30);
        final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
        container = ProviderContainer(overrides: [servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db))]);
        return UncontrolledProviderScope(container: container, child: MaterialApp(home: child));
      });
      return w!;
    }

    Future<void> real(WidgetTester t) async {
      await t.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
      await t.pump();
    }

    testWidgets('a draft report can be read and marked reviewed, but not edited', (tester) async {
      await tester.pumpWidget(await host(tester, {'POST /reports/r1/review': (200, {'status': 'reviewed'})},
          ReportScreen(report: _draftReport, projectId: 'p1', projectTitle: 'Chioma\'s bungalow')));
      await tester.pumpAndSettle();

      expect(find.text('AI-generated draft'), findsOneWidget);
      expect(find.text('Needs your review'), findsOneWidget);
      expect(find.text('EV-2246'), findsOneWidget);
      expect(find.textContaining('Held by a licensed escrow partner'), findsOneWidget);
      expect(find.text('Edit'), findsNothing); // review-only
      expect(find.byType(TextField), findsNothing);

      await tester.tap(find.text('Mark reviewed'));
      await tester.pumpAndSettle();
      expect(find.text('Mark this report reviewed?'), findsOneWidget);
      expect(server.seen.where((r) => r.method == 'POST'), isEmpty); // nothing sent until confirmed
      await tester.tap(find.text('Mark reviewed').last);
      await tester.pumpAndSettle();
      final post = server.seen.singleWhere((r) => r.method == 'POST');
      expect(post.path, '/reports/r1/review');
      expect(post.headers['Idempotency-Key'], isNotEmpty);
    });

    testWidgets('a report that is already reviewed has no review button', (tester) async {
      await tester.pumpWidget(await host(tester, {}, ReportScreen(report: {..._draftReport, 'status': 'reviewed'}, projectId: 'p1')));
      await tester.pumpAndSettle();
      expect(find.text('Reviewed'), findsOneWidget);
      expect(find.text('Mark reviewed'), findsNothing);
    });

    testWidgets('spot checks: assigned and done are grouped, with the do-not-tell notice', (tester) async {
      final soon = DateTime.now().toUtc().add(const Duration(days: 3)).toIso8601String();
      await tester.pumpWidget(await host(tester, {
        'GET /supervisors/me/spot-checks': (200, [
          {'id': 's1', 'project_id': 'p1', 'scheduled_for': soon, 'completed_at': null, 'findings': null},
          {'id': 's2', 'project_id': 'p2', 'scheduled_for': '2026-12-01T09:00:00Z', 'completed_at': '2026-12-01T10:00:00Z', 'findings': 'Matched.'},
        ]),
      }, const Scaffold(body: SpotChecksScreen())));
      await tester.pumpAndSettle();
      expect(find.textContaining('Don\'t tell the contractor'), findsOneWidget);
      expect(find.text('ASSIGNED'), findsOneWidget);
      expect(find.text('DONE'), findsOneWidget);
      expect(find.text('Scheduled'), findsOneWidget);
      expect(find.text('Submitted'), findsOneWidget);
    });

    testWidgets('orders show sample orders clearly labelled, with money from whole kobo', (tester) async {
      await tester.pumpWidget(await host(tester, {}, const Scaffold(body: OrdersTab())));
      await tester.pumpAndSettle();
      expect(find.textContaining('Sample orders'), findsOneWidget);
      expect(find.text('₦349,500'), findsOneWidget);
      expect(find.text('Waiting for the client'), findsOneWidget);
      expect(find.text('Paid'), findsOneWidget);
      expect(find.text('Request materials'), findsOneWidget);
    });

    testWidgets('alerts show sample alerts clearly labelled, with the unread one marked', (tester) async {
      await tester.pumpWidget(await host(tester, {}, const Scaffold(body: AlertsTab())));
      await tester.pumpAndSettle();
      expect(find.textContaining('Sample alerts'), findsOneWidget);
      expect(find.textContaining('(unread)'), findsOneWidget); // not by the blue dot alone
    });

    testWidgets('delivery: the count step needs a photo for every line before it confirms', (tester) async {
      final order = {
        '_mock': true,
        'id': 'o1',
        'project_id': 'p1',
        'display_ref': 'O-0141',
        'supplier': 'Sample Building Materials',
        'milestone': 'Plastering',
        'total_minor': 217200000,
        'currency': 'NGN',
        'items': [
          {'item': 'Cement, 50 kg bag', 'unit': 'bag', 'quantity': '140', 'unit_price_minor': 1030000},
          {'item': 'Sharp sand', 'unit': 'tonne', 'quantity': '20', 'unit_price_minor': 2150000},
        ],
      };
      await tester.pumpWidget(await host(tester, {}, CountDeliveryScreen(order: order)));
      await real(tester);
      expect(find.text('2 photos still needed'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Confirm delivery')).onPressed, isNull);

      // The counts start at what was ordered and move one at a time.
      expect(find.text('140'), findsOneWidget);
      await tester.tap(find.byTooltip('Decrease Cement, 50 kg bag'));
      await tester.pump();
      expect(find.text('139'), findsOneWidget);
    });
  });
}
