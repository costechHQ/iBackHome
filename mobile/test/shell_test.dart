import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ibackhome_mobile/core/wat.dart';
import 'package:ibackhome_mobile/ui/ibh_app_bar.dart';
import 'package:ibackhome_mobile/ui/ibh_card.dart';
import 'package:ibackhome_mobile/ui/states.dart';

void main() {
  group('WAT', () {
    // 12:24 UTC is 13:24 in Nigeria (UTC+1, no daylight saving).
    final t = DateTime.utc(2026, 1, 6, 12, 24);

    test('shows Nigerian time whatever the phone zone is', () {
      expect(watClock(t), '13:24');
      expect(watTime(t), '13:24 WAT');
      expect(watDay(t), 'Tue 6 Jan');
      expect(watDayTime(t), 'Tue 6 Jan, 13:24 WAT');
    });

    test('rolls the day over after 23:00 UTC', () {
      final late = DateTime.utc(2026, 1, 6, 23, 30);
      expect(watDay(late), 'Wed 7 Jan');
      expect(watClock(late), '00:30');
    });
  });

  testWidgets('app bar shows the title, the subtitle and a 48dp back target', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Navigator(
        onGenerateRoute: (_) => MaterialPageRoute<void>(
          builder: (_) => const Scaffold(appBar: IbhAppBar(title: 'Arrival check', subtitle: 'Chioma\'s bungalow')),
        ),
      ),
    ));
    expect(find.text('Arrival check'), findsOneWidget);
    expect(find.text('Chioma\'s bungalow'), findsOneWidget);
    final back = tester.getSize(find.byTooltip('Back'));
    expect(back.width, greaterThanOrEqualTo(48));
    expect(back.height, greaterThanOrEqualTo(48));
  });

  testWidgets('a group puts a hairline between rows and rows are at least 48dp', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(body: IbhGroup(children: [IbhRow(title: 'A'), IbhRow(title: 'B', subtitle: 'two')])),
    ));
    expect(find.byType(Divider), findsOneWidget);
    expect(tester.getSize(find.byType(IbhRow).first).height, greaterThanOrEqualTo(48));
  });

  testWidgets('empty state names the reason and shows a button only when given one', (tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: EmptyState(icon: Icons.inbox, title: 'No projects assigned', message: 'iBackHome will assign you.'),
      ),
    ));
    expect(find.text('No projects assigned'), findsOneWidget);
    expect(find.byType(OutlinedButton), findsNothing);
  });

  testWidgets('bottom action bar stacks or splits its buttons', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        bottomNavigationBar: BottomActionBar(row: true, children: [
          OutlinedButton(onPressed: () {}, child: const Text('Retake')),
          FilledButton(onPressed: () {}, child: const Text('Save')),
        ]),
      ),
    ));
    expect(find.text('Retake'), findsOneWidget);
    expect(find.text('Save'), findsOneWidget);
    expect(tester.getTopLeft(find.text('Retake')).dy, tester.getTopLeft(find.text('Save')).dy);
  });
}
