import 'dart:convert';

import 'package:material_ui/material_ui.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const NammaRideApp());

class NammaRideApp extends StatelessWidget {
  const NammaRideApp({super.key, this.client});
  final http.Client? client;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Namma Ride Driver',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF166547)),
      scaffoldBackgroundColor: const Color(0xFFF4F7F4),
      useMaterial3: true,
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
    ),
    home: PilotScreen(client: client),
  );
}

class PilotScreen extends StatefulWidget {
  const PilotScreen({super.key, this.client});
  final http.Client? client;

  @override
  State<PilotScreen> createState() => _PilotScreenState();
}

class _PilotScreenState extends State<PilotScreen> {
  final formKey = GlobalKey<FormState>();
  final server = TextEditingController(
    text: const String.fromEnvironment('API_BASE_URL'),
  );
  late final http.Client client = widget.client ?? http.Client();
  String status = 'Enter the test server address to connect.';
  bool busy = false;
  bool connected = false;

  @override
  void dispose() {
    server.dispose();
    if (widget.client == null) client.close();
    super.dispose();
  }

  String? validateServer(String? value) {
    final uri = Uri.tryParse((value ?? '').trim());
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment) {
      return 'Enter an HTTP or HTTPS server URL, without credentials.';
    }
    return null;
  }

  Future<void> checkApi() async {
    if (!formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      busy = true;
      connected = false;
      status = 'Connecting to your pilot server…';
    });
    String message;
    bool success = false;
    try {
      final base = server.text.trim().replaceFirst(RegExp(r'/+$'), '');
      final response = await client
          .get(Uri.parse('$base/api/v1/pilot'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) {
        message =
            'Server returned ${response.statusCode}. Check the API address.';
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        if (data['name'] != 'Namma Ride' ||
            data['location'] != 'Madurantakam' ||
            data['customer_limit'] != 100 ||
            data['driver_limit'] != 10) {
          throw const FormatException('Unexpected pilot configuration');
        }
        message = 'Connected to the Madurantakam pilot.';
        success = true;
      }
    } on FormatException {
      message =
          'This server did not return the expected Namma Ride pilot data.';
    } catch (_) {
      message = 'Cannot reach the server. Check the address, Wi-Fi and backend. Localhost on a phone means the phone itself.';
    }
    if (!mounted) return;
    setState(() {
      status = message;
      connected = success;
      busy = false;
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Namma Ride · Driver')),
    body: SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Chip(
                  avatar: Icon(Icons.science_outlined, size: 18),
                  label: Text('PRIVATE TEST · PHASE 1'),
                ),
                const SizedBox(height: 20),
                const Icon(
                  Icons.drive_eta_outlined,
                  size: 54,
                  color: Color(0xFF166547),
                ),
                const SizedBox(height: 16),
                Text(
                  'Vanakkam, Madurantakam!',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Your driver companion for the Madurantakam private pilot.',
                ),
                const SizedBox(height: 24),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Pilot community',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        const Text('100 customers · 10 drivers'),
                        const SizedBox(height: 8),
                        const Text('Madurantakam, Tamil Nadu'),
                        const SizedBox(height: 8),
                        const Text('Bike Taxi · Demo only'),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  'Connect to the test server',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                Form(
                  key: formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      TextFormField(
                        controller: server,
                        validator: validateServer,
                        enabled: !busy,
                        keyboardType: TextInputType.url,
                        autocorrect: false,
                        decoration: const InputDecoration(
                          labelText: 'API server URL',
                          hintText: 'https://your-test-server.example',
                          helperText: 'Use HTTPS for a hosted server. Address is kept for this session.',
                        ),
                        onFieldSubmitted: (_) {
                          if (!busy) checkApi();
                        },
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: busy ? null : checkApi,
                        icon: busy
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Icon(Icons.wifi_tethering),
                        label: Text(
                          busy ? 'Connecting…' : 'Check API connection',
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Semantics(
                  liveRegion: true,
                  child: Text(
                    status,
                    style: TextStyle(
                      color: connected ? const Color(0xFF166547) : null,
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                const Divider(),
                const SizedBox(height: 12),
                const Text(
                  'Foundation test build',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                const Text(
                  'No public ride operations or real payments. Bike Taxi is demo-only. Booking, dispatch, sign-in and live tracking are not enabled. This app verifies the pilot API connection.',
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
