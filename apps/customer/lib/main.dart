import 'package:http/http.dart' as http;
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
        km <= 0) {
      setState(
        () => message = 'Enter pickup, drop-off and a positive demo distance.',
      );
      return;
    }
    final ride = await api!.book(
      pickup: pickup.text,
      dropoff: dropoff.text,
      distance: km,
    );
    setState(
      () => message =
          'Ride #${ride['id']} requested. Estimated fare ₹${ride['estimated_fare_rupees']} (demo only).',
    );
    await refresh();
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
          const Chip(label: Text('PRIVATE TEST · PHASE 2')),
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
    return Card(
      child: ListTile(
        title: Text('#${ride['id']} · ${ride['status']}'),
        subtitle: Text(
          '${ride['pickup']} → ${ride['dropoff']}\nDemo estimate ₹${ride['estimated_fare_rupees']}${driver == null ? '\nWaiting for a driver' : '\nDriver: ${driver['display_name']} · ${driver['vehicle_number'] ?? 'vehicle pending'} · ${driver['phone']}'}',
        ),
        isThreeLine: true,
        trailing: ['requested', 'accepted'].contains(ride['status'])
            ? TextButton(
                onPressed: busy ? null : () => cancel(ride['id'] as int),
                child: const Text('Cancel'),
              )
            : null,
      ),
    );
  }
}
