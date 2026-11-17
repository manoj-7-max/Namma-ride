import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:namma_ride_driver/main.dart';

void main() {
  testWidgets('shows approval-gated Phase 3 registration', (tester) async {
    await tester.pumpWidget(const NammaRideDriverApp());
    expect(find.text('PRIVATE TEST · PHASE 3'), findsOneWidget);
    expect(find.textContaining('Admin approval'), findsOneWidget);
    expect(find.textContaining('No real payments'), findsOneWidget);
  });

  testWidgets('driver signs in and sees pending approval', (tester) async {
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/otp/request')) {
        return http.Response(
          jsonEncode({'challenge_id': 8, 'test_otp': '654321'}),
          200,
        );
      }
      if (request.url.path.endsWith('/otp/verify')) {
        return http.Response(
          jsonEncode({
            'access_token': 'token',
            'user': {
              'id': 2,
              'display_name': 'Selvi',
              'phone': '+919876543211',
              'role': 'driver',
              'driver_approved': false,
              'vehicle_number': 'TN19AB1234',
            },
          }),
          200,
        );
      }
      return http.Response('{}', 404);
    });
    await tester.pumpWidget(NammaRideDriverApp(client: client));
    await tester.enterText(
      find.byType(TextField).at(0),
      'https://pilot.example',
    );
    await tester.enterText(find.byType(TextField).at(1), '9876543211');
    await tester.enterText(find.byType(TextField).at(2), 'Selvi');
    await tester.enterText(find.byType(TextField).at(3), 'TN19AB1234');
    await tester.tap(find.text('Request test OTP'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(4), '654321');
    await tester.tap(find.text('Verify and sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Vanakkam, Selvi!'), findsOneWidget);
    expect(find.textContaining('Approval pending'), findsOneWidget);
  });
}
