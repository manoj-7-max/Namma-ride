import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class CustomerApi {
  CustomerApi(this.baseUrl, this.client);
  final String baseUrl;
  final http.Client client;
  String? token;

  String get base => baseUrl.trim().replaceFirst(RegExp(r'/+$'), '');

  Future<Map<String, dynamic>> requestOtp({
    required String phone,
    required String name,
  }) async => (await _send(
    'POST',
    '/api/v1/auth/otp/request',
    body: {'phone': phone, 'role': 'customer', 'display_name': name},
  )) as Map<String, dynamic>;

  Future<Map<String, dynamic>> verifyOtp({
    required int challengeId,
    required String phone,
    required String otp,
  }) async {
    final result = await _send(
      'POST',
      '/api/v1/auth/otp/verify',
      body: {'challenge_id': challengeId, 'phone': phone, 'otp': otp},
    );
    token = result['access_token'] as String;
    return result;
  }

  Future<Map<String, dynamic>> book({
    required String pickup,
    required String dropoff,
    required double distance,
    required double pickupLatitude,
    required double pickupLongitude,
    required double dropoffLatitude,
    required double dropoffLongitude,
  }) async => (await _send(
    'POST',
    '/api/v1/rides',
    authenticated: true,
    body: {
      'pickup': pickup,
      'dropoff': dropoff,
      'estimated_distance_km': distance,
      'pickup_latitude': pickupLatitude,
      'pickup_longitude': pickupLongitude,
      'dropoff_latitude': dropoffLatitude,
      'dropoff_longitude': dropoffLongitude,
    },
  )) as Map<String, dynamic>;

  Future<List<Map<String, dynamic>>> rides() async =>
      (await _send('GET', '/api/v1/rides/mine', authenticated: true) as List)
          .cast<Map<String, dynamic>>();

  Future<Map<String, dynamic>> cancel(int id) async => (await _send(
    'PATCH',
    '/api/v1/rides/$id/status',
    authenticated: true,
    body: {
      'status': 'cancelled',
      'cancellation_reason': 'Cancelled in Customer app',
    },
  )) as Map<String, dynamic>;

  Future<Map<String, dynamic>> rematch(int id) async =>
      (await _send('POST', '/api/v1/rides/$id/rematch', authenticated: true))
          as Map<String, dynamic>;

  Stream<Map<String, dynamic>> watchEvents(
    int rideId, {
    int afterId = 0,
  }) async* {
    final request = http.Request(
      'GET',
      Uri.parse('$base/api/v1/rides/$rideId/events/stream?after_id=$afterId'),
    )..headers['Authorization'] = 'Bearer $token';
    final response = await client
        .send(request)
        .timeout(const Duration(seconds: 10));
    if (response.statusCode != 200) {
      throw ApiException('Live updates unavailable (${response.statusCode})');
    }
    await for (final line
        in response.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())) {
      if (line.startsWith('data: ')) {
        yield (jsonDecode(line.substring(6)) as Map).cast<String, dynamic>();
      }
    }
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool authenticated = false,
  }) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (authenticated) headers['Authorization'] = 'Bearer $token';
    final request = http.Request(method, Uri.parse('$base$path'))
      ..headers.addAll(headers);
    if (body != null) request.body = jsonEncode(body);
    final streamed = await client
        .send(request)
        .timeout(const Duration(seconds: 10));
    final response = await http.Response.fromStream(streamed);
    final decoded = response.body.isEmpty ? null : jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(
        decoded is Map
            ? decoded['detail']?.toString() ?? 'Request failed'
            : 'Request failed (${response.statusCode})',
      );
    }
    return decoded;
  }
}
