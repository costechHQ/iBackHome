import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/api.dart';
import 'package:ibackhome_mobile/core/geo.dart';
import 'package:ibackhome_mobile/core/money.dart';
import 'package:ibackhome_mobile/core/queue_db.dart';
import 'package:ibackhome_mobile/core/services.dart';
import 'package:ibackhome_mobile/core/token_store.dart';
import 'package:ibackhome_mobile/features/milestone_screen.dart';
import 'package:ibackhome_mobile/features/projects_tab.dart';
import 'package:ibackhome_mobile/features/queue_screen.dart';
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

final _contractor = {'id': 'u1', 'role': 'contractor', 'status': 'active', 'full_name': 'Obinna Obi', 'timezone': 'Africa/Lagos', 'consent_required': false};

final _project = {
  'id': 'p1',
  'title': 'Chioma\'s bungalow',
  'address': 'Independence Layout',
  'status': 'active',
  'currency': 'NGN',
  'budget_minor': 1000000000,
  'site': null,
};

Map<String, Object?> _milestone(int n, String name, String status, {int amount = 543300000}) => {
      'id': 'm$n',
      'project_id': 'p1',
      'sequence': n,
      'name': name,
      'amount_minor': amount,
      'currency': 'NGN',
      'status': status,
      'claimed_at': null,
      'latest_verification': null,
    };

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  group('money', () {
    test('groups the naira and drops empty kobo', () {
      expect(formatMoney(543300000), '₦5,433,000');
      expect(formatMoney(100), '₦1');
      expect(formatMoney(0), '₦0');
    });

    test('keeps the kobo when there are some, and never rounds', () {
      expect(formatMoney(125050), '₦1,250.50');
      expect(formatMoney(5), '₦0.05');
    });

    test('another currency shows its code', () {
      expect(formatMoney(420000, currency: 'GBP'), 'GBP 4,200');
    });
  });

  test('distance to the nearest edge works from inside and outside a plot', () {
    // A square about 100 m on a side near Enugu: [lon, lat].
    final ring = [
      [7.4900, 6.4500],
      [7.4909, 6.4500],
      [7.4909, 6.4509],
      [7.4900, 6.4509],
      [7.4900, 6.4500],
    ];
    final inside = Geo.distanceToEdge(ring, 6.45045, 7.49045); // the middle: about 50 m from every edge
    expect(inside, inInclusiveRange(40, 60));
    final outside = Geo.distanceToEdge(ring, 6.45045, 7.4915); // east of the plot
    expect(outside, greaterThan(50));
    expect(Geo.inside(ring, 6.45045, 7.49045), isTrue);
  });

  group('screens against a fake server', () {
    late Directory tmp;
    late QueueDb db;
    late ProviderContainer container;
    late _Server server;

    setUp(() async {
      tmp = await Directory.systemTemp.createTemp('ibh_rel');
      db = await QueueDb.open(path: '${tmp.path}/q.db');
    });

    tearDown(() async {
      container.dispose();
      await db.close();
      await tmp.delete(recursive: true);
    });

    // The fake server and the sign-in run in real time (outside the test clock), as in the profile tests.
    Future<Widget> host(WidgetTester tester, Map<String, (int, Object)> routes, Widget child) async {
      final w = await tester.runAsync(() async {
        server = _Server({'GET /me': (200, _contractor), ...routes});
        final tokens = TokenStore(_Store());
        await tokens.save('a', 'r' * 30);
        final api = Api(tokens, dio: Dio(BaseOptions(baseUrl: 'http://test'))..httpClientAdapter = server);
        container = ProviderContainer(overrides: [servicesProvider.overrideWithValue(Services.forTesting(tokens: tokens, api: api, db: db))]);
        await container.read(authProvider.notifier).restore();
        return UncontrolledProviderScope(container: container, child: MaterialApp(home: child));
      });
      return w!;
    }

    testWidgets('a contractor sees each project with its progress and what to do next', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects': (200, {'items': [_project], 'next_cursor': null}),
        'GET /projects/p1/milestones': (200, [
          _milestone(1, 'Foundation', 'released'),
          _milestone(2, 'Blockwork', 'released'),
          _milestone(3, 'Plastering', 'funded'),
        ]),
      }, const Scaffold(body: ProjectsTab())));
      await tester.pumpAndSettle();

      expect(find.text('Good '), findsNothing); // the greeting includes the first name
      expect(find.textContaining('Obinna'), findsOneWidget);
      expect(find.text('Chioma\'s bungalow'), findsOneWidget);
      expect(find.textContaining('2 of 3 released'), findsOneWidget);
      expect(find.text('Plastering: ready to claim ›'), findsOneWidget);
      expect(find.textContaining('payouts are on the web portal'), findsOneWidget);
    });

    testWidgets('claiming asks first, then sends the claim with an Idempotency-Key', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects/p1': (200, _project),
        'GET /projects/p1/milestones': (200, [_milestone(3, 'Plastering', 'funded')]),
        'POST /milestones/m3/claim': (200, {'status': 'claimed'}),
      }, const MilestoneScreen(projectId: 'p1', milestoneId: 'm3')));
      await tester.pumpAndSettle();

      expect(find.text('₦5,433,000'), findsOneWidget);
      expect(find.text('Held by a licensed escrow partner, never by iBackHome.'), findsOneWidget);
      await tester.tap(find.text('Claim milestone'));
      await tester.pumpAndSettle();
      expect(find.text('Claim Plastering?'), findsOneWidget);
      expect(server.seen.where((r) => r.method == 'POST'), isEmpty); // nothing sent until confirmed

      await tester.tap(find.text('Claim milestone').last);
      await tester.pumpAndSettle();
      final claim = server.seen.singleWhere((r) => r.method == 'POST');
      expect(claim.path, '/milestones/m3/claim');
      expect(claim.headers['Idempotency-Key'], isNotEmpty);
    });

    testWidgets('a milestone that is already claimed cannot be claimed again', (tester) async {
      await tester.pumpWidget(await host(tester, {
        'GET /projects/p1': (200, _project),
        'GET /projects/p1/milestones': (200, [_milestone(3, 'Plastering', 'claimed')]),
      }, const MilestoneScreen(projectId: 'p1', milestoneId: 'm3')));
      await tester.pumpAndSettle();
      expect(find.text('Claim milestone'), findsNothing);
    });

    testWidgets('the Sync tab says everything is uploaded when nothing is waiting', (tester) async {
      await tester.pumpWidget(await host(tester, {}, const Scaffold(body: QueueScreen())));
      // The queue reads the phone's database, which is real I/O: give it real time, then draw.
      await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 300)));
      await tester.pump();
      expect(find.text('Everything uploaded'), findsOneWidget);
    });
  });
}
