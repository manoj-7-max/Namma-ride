import 'dart:convert';

import 'package:material_ui/material_ui.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:namma_ride_driver/main.dart';

void main() {
  testWidgets('shows pilot screen and rejects invalid server', (tester) async {
    await tester.pumpWidget(const NammaRideApp());
    expect(find.text('Namma Ride · Driver'), findsOneWidget);
    expect(find.text('Bike Taxi · Demo only'), findsOneWidget);
    await tester.ensureVisible(find.text('Check API connection'));
    await tester.tap(find.text('Check API connection'));
    await tester.pumpAndSettle();
    expect(
      find.text('Enter an HTTP or HTTPS server URL, without credentials.'),
      findsOneWidget,
    );
  });

  testWidgets('connects to configured server and validates pilot', (
    tester,
  ) async {
    final client = MockClient((request) async {
      expect(request.url.toString(), 'https://pilot.example/api/v1/pilot');
      return http.Response(
        jsonEncode({
          'name': 'Namma Ride',
          'location': 'Madurantakam',
          'customer_limit': 100,
          'driver_limit': 10,
        }),
        200,
      );
    });
    await tester.pumpWidget(NammaRideApp(client: client));
    await tester.enterText(
      find.byType(TextFormField),
      'https://pilot.example/',
    );
    await tester.ensureVisible(find.text('Check API connection'));
    await tester.tap(find.text('Check API connection'));
    await tester.pumpAndSettle();
    expect(find.text('Connected to the Madurantakam pilot.'), findsOneWidget);
    client.close();
  });

  testWidgets('shows server failures without claiming connection', (
    tester,
  ) async {
    final client = MockClient((_) async => http.Response('Unavailable', 503));
    await tester.pumpWidget(NammaRideApp(client: client));
    await tester.enterText(find.byType(TextFormField), 'https://pilot.example');
    await tester.ensureVisible(find.text('Check API connection'));
    await tester.tap(find.text('Check API connection'));
    await tester.pumpAndSettle();
    expect(
      find.text('Server returned 503. Check the API address.'),
      findsOneWidget,
    );
    client.close();
  });
}
