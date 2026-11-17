import 'dart:convert';

import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
}

class DriverApi {
  DriverApi(this.baseUrl, this.client);
  final String baseUrl;
  final http.Client client;
  String? token;
  String get base => baseUrl.trim().replaceFirst(RegExp(r'/+$'), '');

  Future<Map<String, dynamic>> requestOtp(
    String phone,
    String name,
    String vehicle,
  ) async => (await _send(
    'POST',
    '/api/v1/auth/otp/request',
    body: {
      'phone': phone,
      'role': 'driver',
      'display_name': name,
      'vehicle_number': vehicle,
    },
  )) as Map<String, dynamic>;
  Future<Map<String, dynamic>> verifyOtp(
    int challengeId,
    String phone,
    String otp,
  ) async {
    final result = await _send(
      'POST',
      '/api/v1/auth/otp/verify',
      body: {'challenge_id': challengeId, 'phone': phone, 'otp': otp},
    );
    token = result['access_token'] as String;
    return result;
  }

  Future<List<Map<String, dynamic>>> requests() async =>
      (await _send('GET', '/api/v1/driver/requests', auth: true) as List)
          .cast<Map<String, dynamic>>();
  Future<List<Map<String, dynamic>>> rides() async =>
      (await _send('GET', '/api/v1/rides/mine', auth: true) as List)
          .cast<Map<String, dynamic>>();
  Future<void> reject(int id) async =>
      _send('POST', '/api/v1/driver/requests/$id/reject', auth: true);
  Future<Map<String, dynamic>> accept(int id) async =>
      (await _send('POST', '/api/v1/driver/requests/$id/accept', auth: true))
          as Map<String, dynamic>;
  Future<Map<String, dynamic>> status(int id, String status) async =>
      (await _send(
        'PATCH',
        '/api/v1/rides/$id/status',
        auth: true,
        body: {'status': status},
      )) as Map<String, dynamic>;

  Future<Map<String, dynamic>> updateLocation({
    required double latitude,
    required double longitude,
    required double accuracy,
    required bool available,
  }) async => (await _send(
    'PUT',
    '/api/v1/driver/location',
    auth: true,
    body: {
      'latitude': latitude,
      'longitude': longitude,
      'accuracy_m': accuracy,
      'captured_at': DateTime.now().toUtc().toIso8601String(),
      'available': available,
    },
  )) as Map<String, dynamic>;

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
    bool auth = false,
  }) async {
    final request = http.Request(method, Uri.parse('$base$path'))
      ..headers['Content-Type'] = 'application/json';
    if (auth) request.headers['Authorization'] = 'Bearer $token';
    if (body != null) request.body = jsonEncode(body);
    final response = await http.Response.fromStream(
      await client.send(request).timeout(const Duration(seconds: 10)),
    );
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
