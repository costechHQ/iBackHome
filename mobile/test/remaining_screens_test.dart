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

    Map<String, Object?> order(String id, String status, {String supplier = 'Ugwu Building Materials', int total = 34950000, List<Map<String, Object?>>? items, Map<String, Object?>? delivery, String created = '2026-12-15T14:22:00Z'}) => {
          'id': id,
          'project_id': 'p1',
          'supplier_id': 's1',
          'requested_by': 'u1',
          'supplier': {'id': 's1', 'name': supplier},
          'items': items ??
              [
                {'item': 'Cement, 50 kg bag', 'unit': 'bag', 'quantity': '120', 'unit_price_minor': 1030000},
                {'item': 'Sharp sand', 'unit': 'tonne', 'quantity': '20', 'unit_price_minor': 2150000},
              ],
          'total_minor': total,
          'currency': 'NGN',
          'status': status,
          'approved_by': null,
          'approved_at': status == 'requested' ? null : '2026-12-16T09:00:00Z',
          'created_at': created,
          'delivery': delivery,
        };

    testWidgets('orders show the contractor\'s real orders, newest first, with money from whole kobo', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects': (200, {'items': [{'id': 'p1', 'title': 'Chioma\'s bungalow'}], 'next_cursor': null}),
        'GET /projects/p1/orders': (200, {
          'items': [
            order('0141aaaa-0000-0000-0000-000000000000', 'requested', total: 34950000, created: '2027-01-07T10:00:00Z'),
            order('0127bbbb-0000-0000-0000-000000000000', 'paid', supplier: 'Obinna Building Materials', total: 312000000, created: '2026-11-12T09:00:00Z',
                delivery: {'id': 'd1', 'order_id': 'x', 'confirmed_by': 'u2', 'quantities': <Object>[], 'evidence_ids': <Object>[], 'confirmed_at': '2026-11-20T12:00:00Z'}),
          ],
          'next_cursor': null,
        }),
      }, const Scaffold(body: OrdersTab())));
      await tester.pumpAndSettle();
      expect(find.textContaining('Sample'), findsNothing);
      expect(find.text('Ugwu Building Materials'), findsOneWidget);
      expect(find.text('Obinna Building Materials'), findsOneWidget);
      expect(find.text('Cement, 50 kg bag +1 more'), findsNWidgets(2));
      expect(find.textContaining('O-0141 · Chioma\'s bungalow · sent'), findsOneWidget);
      expect(find.textContaining('O-0127 · Chioma\'s bungalow · delivered'), findsOneWidget); // delivered date, not sent
      expect(find.text('₦349,500'), findsOneWidget);
      expect(find.text('₦3,120,000'), findsOneWidget);
      expect(find.text('Waiting for the client'), findsOneWidget);
      expect(find.text('Paid'), findsOneWidget);
      expect(find.text('Request materials'), findsOneWidget);
      // Newest first: the January order is listed above the November one.
      expect(tester.getTopLeft(find.text('Ugwu Building Materials')).dy, lessThan(tester.getTopLeft(find.text('Obinna Building Materials')).dy));
    });

    testWidgets('orders gathers every project and says so when there are none', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects': (200, {'items': [{'id': 'p1', 'title': 'One'}], 'next_cursor': null}),
        'GET /projects/p1/orders': (200, {'items': <Object>[], 'next_cursor': null}),
      }, const Scaffold(body: OrdersTab())));
      await tester.pumpAndSettle();
      expect(find.text('No orders yet'), findsOneWidget);
    });

    testWidgets('deliveries lists only approved orders, to be counted', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects/p1/orders': (200, {
          'items': [
            order('0141aaaa-0000-0000-0000-000000000000', 'approved'),
            order('0150bbbb-0000-0000-0000-000000000000', 'requested', supplier: 'Not yet approved'),
            order('0160cccc-0000-0000-0000-000000000000', 'paid', supplier: 'Already paid'),
          ],
          'next_cursor': null,
        }),
      }, const DeliveriesScreen(projectId: 'p1', projectTitle: 'Chioma\'s bungalow')));
      await tester.pumpAndSettle();
      expect(find.text('Ugwu Building Materials'), findsOneWidget);
      expect(find.text('Not yet approved'), findsNothing);
      expect(find.text('Already paid'), findsNothing);
      expect(find.textContaining('O-0141'), findsOneWidget);
    });

    testWidgets('deliveries with nothing approved says so', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects/p1/orders': (200, {'items': <Object>[], 'next_cursor': null}),
      }, const DeliveriesScreen(projectId: 'p1')));
      await tester.pumpAndSettle();
      expect(find.text('No deliveries to confirm'), findsOneWidget);
    });

    Map<String, Object?> alert(String id, String title, String text, {String? readAt}) =>
        {'id': id, 'template': 'milestone.verified', 'title': title, 'text': text, 'created_at': '2026-11-01T09:00:00Z', 'read_at': readAt};

    testWidgets('alerts show what the server sent, with the unread one marked (not by the dot alone)', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /me/notifications': (200, {
          'items': [
            alert('n1', 'Milestone verified', 'Foundation was verified by the supervisor.'),
            alert('n2', 'Milestone funded', 'You can start work.', readAt: '2026-11-01T10:00:00Z'),
          ],
          'next_cursor': null,
          'unread_count': 1,
        }),
      }, const Scaffold(body: AlertsTab())));
      await tester.pumpAndSettle();
      expect(find.textContaining('Sample alerts'), findsNothing);
      expect(find.text('Foundation was verified by the supervisor.'), findsOneWidget);
      expect(find.text('You can start work.'), findsOneWidget);
      expect(find.textContaining('(unread)'), findsOneWidget);
    });

    testWidgets('opening an unread alert marks it read with an Idempotency-Key and reads the list again', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /me/notifications': (200, {
          'items': [alert('n1', 'Milestone verified', 'Foundation was verified by the supervisor.')],
          'next_cursor': null,
          'unread_count': 1,
        }),
        'POST /me/notifications/n1/read': (200, alert('n1', 'Milestone verified', 'Foundation was verified by the supervisor.', readAt: '2026-11-02T08:00:00Z')),
      }, const Scaffold(body: AlertsTab())));
      await tester.pumpAndSettle();
      expect(find.textContaining('(unread)'), findsOneWidget);

      server.routes['GET /me/notifications'] = (200, {
        'items': [alert('n1', 'Milestone verified', 'Foundation was verified by the supervisor.', readAt: '2026-11-02T08:00:00Z')],
        'next_cursor': null,
        'unread_count': 0,
      });
      await tester.tap(find.text('Foundation was verified by the supervisor.'));
      await tester.pumpAndSettle();

      final post = server.seen.singleWhere((r) => r.method == 'POST');
      expect(post.path, '/me/notifications/n1/read');
      expect(post.headers['Idempotency-Key'], 'read-n1');
      expect(find.textContaining('(unread)'), findsNothing);
    });

    testWidgets('a read alert sends nothing when it is tapped', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /me/notifications': (200, {
          'items': [alert('n2', 'Milestone funded', 'You can start work.', readAt: '2026-11-01T10:00:00Z')],
          'next_cursor': null,
          'unread_count': 0,
        }),
      }, const Scaffold(body: AlertsTab())));
      await tester.pumpAndSettle();
      await tester.tap(find.text('You can start work.'));
      await tester.pumpAndSettle();
      expect(server.seen.where((r) => r.method == 'POST'), isEmpty);
    });

    testWidgets('no alerts yet says so', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /me/notifications': (200, {'items': <Object>[], 'next_cursor': null, 'unread_count': 0}),
      }, const Scaffold(body: AlertsTab())));
      await tester.pumpAndSettle();
      expect(find.text('No alerts yet'), findsOneWidget);
    });

    final cementAndSand = [
      {'item': 'Cement, 50 kg bag', 'unit': 'bag', 'quantity': '140', 'unit_price_minor': 1030000},
      {'item': 'Sharp sand', 'unit': 'tonne', 'quantity': '2.5', 'unit_price_minor': 2150000},
    ];

    testWidgets('delivery: the count step needs a photo for every line before it confirms', (tester) async {
      await tester.pumpWidget(await host(tester, {}, CountDeliveryScreen(order: order('o1', 'approved', items: cementAndSand))));
      await real(tester);
      expect(find.text('2 photos still needed'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Confirm delivery')).onPressed, isNull);

      // A whole-number line starts at what was ordered and moves one at a time.
      expect(find.text('140'), findsOneWidget);
      await tester.tap(find.byTooltip('Decrease Cement, 50 kg bag'));
      await tester.pump();
      expect(find.text('139'), findsOneWidget);
      // A line ordered in decimals (2.5 tonnes) is a decimal field, starting at the ordered 2.5.
      expect(find.widgetWithText(TextFormField, '2.5'), findsOneWidget);
      expect(find.text('of 2.5 ordered'), findsOneWidget);
    });

    testWidgets('delivery: a count that is not a number stops the confirm', (tester) async {
      await tester.pumpWidget(await host(tester, {}, CountDeliveryScreen(order: order('o1', 'approved', items: cementAndSand))));
      await real(tester);
      await tester.enterText(find.widgetWithText(TextFormField, '2.5'), '2.5555');
      await tester.pump();
      expect(find.text('Enter a number like 2.5'), findsOneWidget);
    });

    testWidgets('delivery: confirming posts the counts as a list, with the photo evidence ids and one idempotency key', (tester) async {
      // Two accepted photos from this phone, one per line, saved against this delivery.
      await tester.runAsync(() async {
        for (final (i, item) in ['Cement, 50 kg bag', 'Sharp sand'].indexed) {
          await db.insert(QueuedCapture(
            id: 'c$i',
            projectId: 'p1',
            kind: 'photo',
            filePath: '/tmp/c$i.jpg',
            sha256: 'a' * 64,
            capturedAt: DateTime.now().toUtc(),
            gpsTime: DateTime.now().toUtc(),
            lat: 6.45,
            lon: 7.5,
            accuracyM: 8,
            deviceId: 'd',
            signature: 's',
            status: CaptureStatus.accepted,
            evidenceId: 'e000000$i-0000-0000-0000-000000000000',
            checklistItem: item,
            contextRef: 'delivery:o1',
          ));
        }
      });
      await tester.pumpWidget(await host(tester, {
        'POST /orders/o1/delivery': (201, {'id': 'd1', 'order_id': 'o1', 'confirmed_by': 'u2', 'quantities': <Object>[], 'evidence_ids': <Object>[], 'confirmed_at': '2026-12-18T12:00:00Z'}),
      }, CountDeliveryScreen(order: order('o1', 'approved', items: cementAndSand))));
      await real(tester);
      await tester.tap(find.byTooltip('Decrease Cement, 50 kg bag')); // 140 -> 139, sent exactly as counted
      await tester.enterText(find.widgetWithText(TextFormField, '2.5'), '2.25');
      await tester.pump();
      await tester.tap(find.widgetWithText(FilledButton, 'Confirm delivery'));
      await tester.pumpAndSettle();

      final post = server.seen.singleWhere((r) => r.method == 'POST');
      expect(post.path, '/orders/o1/delivery');
      expect(post.headers['Idempotency-Key'], 'delivery-o1');
      expect(post.data, {
        'quantities': [
          {'item': 'Cement, 50 kg bag', 'quantity': '139'},
          {'item': 'Sharp sand', 'quantity': '2.25'},
        ],
        'evidence_ids': ['e0000000-0000-0000-0000-000000000000', 'e0000001-0000-0000-0000-000000000000'],
      });
      expect(find.text('Delivery confirmed'), findsOneWidget);
    });
  });
}
