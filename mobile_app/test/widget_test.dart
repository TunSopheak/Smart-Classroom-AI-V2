import 'package:flutter_test/flutter_test.dart';
import 'package:smart_classroom_mobile/main.dart';

void main() {
  testWidgets('Smart Classroom app launches', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartClassroomApp());

    expect(find.text('Smart Classroom MVP'), findsOneWidget);
  });
}
