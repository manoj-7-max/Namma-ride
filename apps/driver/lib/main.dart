import 'package:http/http.dart' as http;
import 'package:material_ui/material_ui.dart';

import 'api.dart';

void main() => runApp(const NammaRideDriverApp());

class NammaRideDriverApp extends StatelessWidget {
  const NammaRideDriverApp({super.key, this.client});
  final http.Client? client;
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Namma Ride Driver',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorSchemeSeed: const Color(0xFF1D3C62),
      useMaterial3: true,
    ),
    home: DriverHome(client: client),
  );
}

class DriverHome extends StatefulWidget {
  const DriverHome({super.key, this.client});
  final http.Client? client;
  @override
  State<DriverHome> createState() => _DriverHomeState();
}

class _DriverHomeState extends State<DriverHome> {
  final server = TextEditingController(
    text: const String.fromEnvironment('API_BASE_URL'),
  );
  final phone = TextEditingController();
  final name = TextEditingController();
  final vehicle = TextEditingController();
  final otp = TextEditingController();
  late final http.Client httpClient = widget.client ?? http.Client();
  DriverApi? api;
  int? challengeId;
  bool approved = false;
  bool busy = false;
  String? driverName;
  String message = 'Register or sign in. Admin approval is required for rides.';
  List<Map<String, dynamic>> requests = [];
  List<Map<String, dynamic>> rides = [];

  @override
  void dispose() {
    for (final controller in [server, phone, name, vehicle, otp]) {
      controller.dispose();
    }
    if (widget.client == null) {
      httpClient.close();
    }
    super.dispose();
  }

  bool get loggedIn => api?.token != null;
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
    final uri = Uri.tryParse(server.text.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        phone.text.isEmpty ||
        name.text.isEmpty ||
        vehicle.text.isEmpty) {
      setState(
        () => message = 'API URL, phone, name and vehicle number are required.',
      );
      return;
    }
    api = DriverApi(server.text, httpClient);
    final result = await api!.requestOtp(phone.text, name.text, vehicle.text);
    setState(() {
      challengeId = result['challenge_id'] as int;
      message = result['test_otp'] == null
          ? 'OTP requested. Ask the private-test operator for the code.'
          : 'Test OTP: ${result['test_otp']}';
    });
  });

  Future<void> verifyOtp() => run(() async {
    if (challengeId == null || otp.text.length != 6) {
      setState(() => message = 'Enter the six-digit OTP.');
      return;
    }
    final result = await api!.verifyOtp(challengeId!, phone.text, otp.text);
    final user = result['user'] as Map<String, dynamic>;
    setState(() {
      driverName = user['display_name'] as String;
      approved = user['driver_approved'] as bool;
      message = approved
          ? 'Signed in and approved.'
          : 'Signed in. Waiting for admin approval.';
    });
    if (approved) await refresh();
  });

  Future<void> refresh() async {
    try {
      final available = await api!.requests();
      final assigned = await api!.rides();
      if (mounted) {
        setState(() {
          requests = available;
          rides = assigned;
          approved = true;
          message = 'Ride lists refreshed.';
        });
      }
    } on ApiException catch (error) {
      if (error.message.contains('approval')) {
        setState(() {
          approved = false;
          message = 'Waiting for admin approval.';
        });
        return;
      }
      rethrow;
    }
  }

  Future<void> accept(int id) => run(() async {
    await api!.accept(id);
    await refresh();
  });
  Future<void> reject(int id) => run(() async {
    await api!.reject(id);
    await refresh();
  });
  Future<void> advance(int id, String state) => run(() async {
    await api!.status(id, state);
    await refresh();
  });

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Namma Ride · Driver')),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Chip(label: Text('PRIVATE TEST · PHASE 2')),
          const Text('Madurantakam, Tamil Nadu · Bike Taxi demo-only'),
          const SizedBox(height: 16),
          if (!loggedIn) ...authForm() else ...driverDashboard(),
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
    const SizedBox(height: 8),
    TextField(
      controller: phone,
      keyboardType: TextInputType.phone,
      decoration: const InputDecoration(labelText: 'Phone number'),
    ),
    const SizedBox(height: 8),
    TextField(
      controller: name,
      decoration: const InputDecoration(labelText: 'Driver name'),
    ),
    const SizedBox(height: 8),
    TextField(
      controller: vehicle,
      decoration: const InputDecoration(labelText: 'Vehicle number'),
    ),
    const SizedBox(height: 8),
    FilledButton(
      onPressed: busy ? null : requestOtp,
      child: const Text('Request test OTP'),
    ),
    if (challengeId != null) ...[
      const SizedBox(height: 8),
      TextField(
        controller: otp,
        keyboardType: TextInputType.number,
        decoration: const InputDecoration(labelText: 'Six-digit OTP'),
      ),
      FilledButton(
        onPressed: busy ? null : verifyOtp,
        child: const Text('Verify and sign in'),
      ),
    ],
  ];

  List<Widget> driverDashboard() => [
    Text(
      'Vanakkam, $driverName!',
      style: Theme.of(context).textTheme.headlineSmall,
    ),
    Text(
      approved
          ? 'Admin approved · available for demo rides'
          : 'Approval pending · ride requests are locked',
    ),
    FilledButton(
      onPressed: busy ? null : () => run(refresh),
      child: Text(approved ? 'Refresh rides' : 'Check approval'),
    ),
    if (approved) ...[
      Text('Available requests', style: Theme.of(context).textTheme.titleLarge),
      if (requests.isEmpty) const Text('No open requests.'),
      ...requests.map(requestCard),
      Text('My rides', style: Theme.of(context).textTheme.titleLarge),
      ...rides.map(assignedCard),
    ],
  ];

  Widget requestCard(Map<String, dynamic> ride) => Card(
    child: ListTile(
      title: Text('${ride['pickup']} → ${ride['dropoff']}'),
      subtitle: Text('Demo estimate ₹${ride['estimated_fare_rupees']}'),
      trailing: Wrap(
        children: [
          TextButton(
            onPressed: () => reject(ride['id'] as int),
            child: const Text('Reject'),
          ),
          FilledButton(
            onPressed: () => accept(ride['id'] as int),
            child: const Text('Accept'),
          ),
        ],
      ),
    ),
  );

  Widget assignedCard(Map<String, dynamic> ride) {
    const next = {
      'accepted': 'arrived',
      'arrived': 'started',
      'started': 'completed',
    };
    final nextState = next[ride['status']];
    return Card(
      child: ListTile(
        title: Text('#${ride['id']} · ${ride['status']}'),
        subtitle: Text('${ride['pickup']} → ${ride['dropoff']}'),
        trailing: nextState == null
            ? null
            : FilledButton(
                onPressed: () => advance(ride['id'] as int, nextState),
                child: Text(nextState.toUpperCase()),
              ),
      ),
    );
  }
}
