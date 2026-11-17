import 'dart:async';

import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:material_ui/material_ui.dart';

import 'api.dart';

void main() => runApp(const NammaRideCustomerApp());

class NammaRideCustomerApp extends StatelessWidget {
  const NammaRideCustomerApp({super.key, this.client});
  final http.Client? client;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Namma Ride Customer',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorSchemeSeed: const Color(0xFF166547),
      useMaterial3: true,
    ),
    home: CustomerHome(client: client),
  );
}

class CustomerHome extends StatefulWidget {
  const CustomerHome({super.key, this.client});
  final http.Client? client;
  @override
  State<CustomerHome> createState() => _CustomerHomeState();
}

class _CustomerHomeState extends State<CustomerHome> {
  final server = TextEditingController(
    text: const String.fromEnvironment('API_BASE_URL'),
  );
  final phone = TextEditingController();
  final name = TextEditingController();
  final otp = TextEditingController();
  final pickup = TextEditingController();
  final dropoff = TextEditingController();
  final distance = TextEditingController();
  late final http.Client httpClient = widget.client ?? http.Client();
  CustomerApi? api;
  int? challengeId;
  String? testOtp;
  String? userName;
  List<Map<String, dynamic>> rides = [];
  String message = 'Register or sign in with your phone number.';
  bool busy = false;
  LatLng? pickupPoint = const LatLng(12.508, 79.884);
  LatLng? dropoffPoint = const LatLng(12.515, 79.89);
  Timer? polling;

  @override
  void dispose() {
    for (final controller in [
      server,
      phone,
      name,
      otp,
      pickup,
      dropoff,
      distance,
    ]) {
      controller.dispose();
    }
    if (widget.client == null) httpClient.close();
    polling?.cancel();
    super.dispose();
  }

  bool get loggedIn => api?.token != null;
  String? serverError() {
    final uri = Uri.tryParse(server.text.trim());
    return uri == null ||
            !['http', 'https'].contains(uri.scheme) ||
            uri.host.isEmpty
        ? 'Enter a valid API URL.'
        : null;
  }

  Future<void> run(Future<void> Function() action) async {
    setState(() => busy = true);
    try {
      await action();
    } on ApiException catch (error) {
      setState(() => message = error.message);
    } catch (_) {
      setState(() => message = 'Cannot reach the private test server.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> requestOtp() => run(() async {
    final error = serverError();
    if (error != null ||
        phone.text.trim().isEmpty ||
        name.text.trim().isEmpty) {
      setState(() => message = error ?? 'Phone and name are required.');
      return;
    }
    api = CustomerApi(server.text, httpClient);
    final result = await api!.requestOtp(phone: phone.text, name: name.text);
    setState(() {
      challengeId = result['challenge_id'] as int;
      testOtp = result['test_otp'] as String?;
      message = testOtp == null
          ? 'OTP requested. Ask the private-test operator for the code.'
          : 'Test OTP: $testOtp';
    });
  });

  Future<void> verifyOtp() => run(() async {
    if (challengeId == null || otp.text.length != 6) {
      setState(() => message = 'Enter the six-digit OTP.');
      return;
    }
    final result = await api!.verifyOtp(
      challengeId: challengeId!,
      phone: phone.text,
      otp: otp.text,
    );
    setState(() {
      userName =
          (result['user'] as Map<String, dynamic>)['display_name'] as String;
      message = 'Signed in. You can book a demo ride.';
    });
    await refresh();
    polling = Timer.periodic(const Duration(seconds: 8), (_) async {
      if (!mounted || busy) return;
      try {
        await refresh();
      } catch (_) {
        if (mounted) {
          setState(() => message = 'Offline · retrying status sync…');
        }
      }
    });
  });

  Future<void> refresh() async {
    final result = await api!.rides();
    if (mounted) setState(() => rides = result);
  }

  Future<void> book() => run(() async {
    final km = double.tryParse(distance.text);
    if (pickup.text.trim().length < 3 ||
        dropoff.text.trim().length < 3 ||
        km == null ||
        km <= 0 ||
        pickupPoint == null ||
        dropoffPoint == null) {
      setState(
        () => message = 'Enter route, distance and select both map points.',
      );
      return;
    }
    final ride = await api!.book(
      pickup: pickup.text,
      dropoff: dropoff.text,
      distance: km,
      pickupLatitude: pickupPoint!.latitude,
      pickupLongitude: pickupPoint!.longitude,
      dropoffLatitude: dropoffPoint!.latitude,
      dropoffLongitude: dropoffPoint!.longitude,
    );
    setState(
      () => message =
          'Ride #${ride['id']} requested. Estimated fare ₹${ride['estimated_fare_rupees']} (demo only).',
    );
    await refresh();
  });

  Future<void> useCurrentLocation() => run(() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      setState(
        () => message = 'GPS is off. Enable location services or tap the map.',
      );
      return;
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      setState(
        () => message =
            'Location permission denied. You can select points on the map.',
      );
      return;
    }
    final position = await Geolocator.getCurrentPosition();
    setState(() {
      pickupPoint = LatLng(position.latitude, position.longitude);
      pickup.text = 'Current location';
      message = 'Pickup selected. Tap the map to choose drop-off.';
    });
  });

  Future<void> cancel(int id) => run(() async {
    await api!.cancel(id);
    setState(() => message = 'Ride #$id cancelled.');
    await refresh();
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Namma Ride · Customer')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Chip(label: Text('PRIVATE TEST · PHASE 3')),
          const Text('Madurantakam, Tamil Nadu · Bike Taxi demo-only'),
          const SizedBox(height: 16),
          if (!loggedIn) ...authForm() else ...rideDashboard(),
          const SizedBox(height: 16),
          Text(message, key: const Key('message')),
          const SizedBox(height: 20),
          const Text(
            'No real payments or public ride operations.',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    ),
  );

  List<Widget> authForm() => [
    TextField(
      controller: server,
      decoration: const InputDecoration(labelText: 'Private API URL'),
    ),
    const SizedBox(height: 10),
    TextField(
      controller: phone,
      keyboardType: TextInputType.phone,
      decoration: const InputDecoration(labelText: 'Phone number'),
    ),
    const SizedBox(height: 10),
    TextField(
      controller: name,
      decoration: const InputDecoration(
        labelText: 'Name (required for registration)',
      ),
    ),
    const SizedBox(height: 10),
    FilledButton(
      onPressed: busy ? null : requestOtp,
      child: const Text('Request test OTP'),
    ),
    if (challengeId != null) ...[
      const SizedBox(height: 10),
      TextField(
        controller: otp,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(labelText: 'Six-digit OTP'),
      ),
      const SizedBox(height: 10),
      FilledButton(
        onPressed: busy ? null : verifyOtp,
        child: const Text('Verify and sign in'),
      ),
    ],
  ];

  List<Widget> rideDashboard() => [
    Text(
      'Vanakkam, $userName!',
      style: Theme.of(context).textTheme.headlineSmall,
    ),
    const SizedBox(height: 12),
    SizedBox(
      height: 260,
      child: FlutterMap(
        options: MapOptions(
          initialCenter: const LatLng(12.511, 79.884),
          initialZoom: 13,
          onTap: (_, point) => setState(() {
            if (pickupPoint == null || dropoffPoint != null) {
              pickupPoint = point;
              dropoffPoint = null;
              pickup.text = 'Selected pickup';
            } else {
              dropoffPoint = point;
              dropoff.text = 'Selected drop-off';
            }
          }),
        ),
        children: [
          TileLayer(
            urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            userAgentPackageName: 'in.nammaride.namma_ride_customer.pilot',
          ),
          MarkerLayer(
            markers: [
              if (pickupPoint != null)
                Marker(
                  point: pickupPoint!,
                  child: const Icon(Icons.person_pin_circle),
                ),
              if (dropoffPoint != null)
                Marker(point: dropoffPoint!, child: const Icon(Icons.flag)),
            ],
          ),
          const RichAttributionWidget(
            attributions: [TextSourceAttribution('OpenStreetMap contributors')],
          ),
        ],
      ),
    ),
    TextButton.icon(
      onPressed: busy ? null : useCurrentLocation,
      icon: const Icon(Icons.my_location),
      label: const Text('Use my location for pickup'),
    ),
    TextField(
      controller: pickup,
      decoration: const InputDecoration(labelText: 'Pickup'),
    ),
    const SizedBox(height: 10),
    TextField(
      controller: dropoff,
      decoration: const InputDecoration(labelText: 'Drop-off'),
    ),
    const SizedBox(height: 10),
    TextField(
      controller: distance,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: const InputDecoration(
        labelText: 'Estimated distance (km)',
        helperText: 'Used only for a demo fare estimate',
      ),
    ),
    const SizedBox(height: 10),
    FilledButton(
      onPressed: busy ? null : book,
      child: const Text('Request demo ride'),
    ),
    TextButton(
      onPressed: busy ? null : () => run(refresh),
      child: const Text('Refresh ride status'),
    ),
    ...rides.map(rideCard),
  ];

  Widget rideCard(Map<String, dynamic> ride) {
    final driver = ride['driver'] as Map<String, dynamic>?;
    final location = ride['driver_location'] as Map<String, dynamic>?;
    final eta = ride['driver_eta_minutes'];
    return Card(
      child: ListTile(
        title: Text('#${ride['id']} · ${ride['status']}'),
        subtitle: Text(
          '${ride['pickup']} → ${ride['dropoff']}\nDemo estimate ₹${ride['estimated_fare_rupees']}${driver == null ? '\nMatching nearby drivers…' : '\nDriver: ${driver['display_name']} · ${driver['vehicle_number'] ?? 'vehicle pending'}'}${eta == null ? '' : '\nEstimated ETA: $eta min'}${location == null ? '' : '\nLocation updated: ${location['captured_at']}'}',
        ),
        isThreeLine: true,
        trailing: ride['status'] == 'no_driver_available'
            ? TextButton(
                onPressed: busy
                    ? null
                    : () => run(() async {
                        await api!.rematch(ride['id'] as int);
                        await refresh();
                      }),
                child: const Text('Retry'),
              )
            : ['requested', 'matching', 'accepted'].contains(ride['status'])
            ? TextButton(
                onPressed: busy ? null : () => cancel(ride['id'] as int),
                child: const Text('Cancel'),
              )
            : null,
      ),
    );
  }
}
