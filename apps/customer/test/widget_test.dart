import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:material_ui/material_ui.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:namma_ride_customer/main.dart';

void main() {
  testWidgets('shows private Phase 3 customer registration', (tester) async {
    await tester.pumpWidget(const NammaRideCustomerApp());
    expect(find.text('PRIVATE TEST · PHASE 3'), findsOneWidget);
    expect(find.text('Request test OTP'), findsOneWidget);
    expect(find.textContaining('No real payments'), findsOneWidget);
  });

  testWidgets('registers, verifies and books a demo ride', (tester) async {
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/otp/request')) {
        return http.Response(
          jsonEncode({
            'challenge_id': 7,
            'expires_in_seconds': 300,
            'test_otp': '123456',
          }),
          200,
        );
      }
      if (request.url.path.endsWith('/otp/verify')) {
        return http.Response(
          jsonEncode({
            'access_token': 'token',
            'token_type': 'bearer',
            'user': {
              'id': 1,
              'display_name': 'Anbu',
              'phone': '+919876543210',
              'role': 'customer',
              'driver_approved': false,
              'vehicle_number': null,
            },
          }),
          200,
        );
      }
      if (request.url.path == '/api/v1/rides' && request.method == 'POST') {
        return http.Response(
          jsonEncode({
            'id': 3,
            'status': 'requested',
            'estimated_fare_rupees': 95.0,
          }),
          201,
        );
      }
      if (request.url.path.endsWith('/rides/mine')) {
        return http.Response('[]', 200);
      }
      return http.Response('{}', 404);
    });
    await tester.pumpWidget(NammaRideCustomerApp(client: client));
    await tester.enterText(
      find.byType(TextField).at(0),
      'https://pilot.example',
    );
    await tester.enterText(find.byType(TextField).at(1), '9876543210');
    await tester.enterText(find.byType(TextField).at(2), 'Anbu');
    await tester.tap(find.text('Request test OTP'));
    await tester.pumpAndSettle();
    expect(find.text('Test OTP: 123456'), findsOneWidget);
    await tester.enterText(find.byType(TextField).at(3), '123456');
    await tester.tap(find.text('Verify and sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Vanakkam, Anbu!'), findsOneWidget);
    await tester.enterText(find.byType(TextField).at(0), 'Bus Stand');
    await tester.enterText(find.byType(TextField).at(1), 'Railway Station');
    await tester.scrollUntilVisible(
      find.text('Estimated distance (km)'),
      250,
      scrollable: find
          .descendant(
            of: find.byType(ListView),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Estimated distance (km)'),
      '3',
    );
    await tester.tap(find.text('Request demo ride'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Estimated fare ₹95'), findsOneWidget);
  });
}
