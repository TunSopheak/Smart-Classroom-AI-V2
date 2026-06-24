import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const SmartClassroomApp());
}

class SmartClassroomApp extends StatelessWidget {
  const SmartClassroomApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Smart Classroom',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.indigo),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class SmartClassroomApi {
  SmartClassroomApi(this.baseUrl);

  final String baseUrl;

  Uri endpoint(String path) => Uri.parse('$baseUrl$path');

  Future<Map<String, dynamic>> getJson(String path) async {
    final response = await http.get(endpoint(path)).timeout(const Duration(seconds: 8));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('HTTP ${response.statusCode}: ${response.body}');
    }
    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    throw Exception('Unexpected API response.');
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final TextEditingController _apiController = TextEditingController(
    text: 'http://10.158.139.199:8000',
  );

  int _selectedIndex = 0;
  bool _loading = false;
  String? _error;
  Map<String, dynamic>? _summary;
  List<dynamic> _students = [];
  List<dynamic> _sessions = [];
  Map<String, dynamic>? _iot;

  SmartClassroomApi get api => SmartClassroomApi(_apiController.text.trim());

  @override
  void initState() {
    super.initState();
    _refreshAll();
  }

  @override
  void dispose() {
    _apiController.dispose();
    super.dispose();
  }

  Future<void> _refreshAll() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final summary = await api.getJson('/api/mobile/summary');
      final students = await api.getJson('/api/mobile/students');
      final sessions = await api.getJson('/api/mobile/sessions/today');
      final iot = await api.getJson('/api/mobile/iot/status');

      if (!mounted) return;
      setState(() {
        _summary = summary['summary'] as Map<String, dynamic>?;
        _students = (students['students'] as List<dynamic>?) ?? [];
        _sessions = (sessions['sessions'] as List<dynamic>?) ?? [];
        _iot = iot;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      DashboardPage(summary: _summary, iot: _iot),
      StudentsPage(students: _students),
      SessionsPage(sessions: _sessions),
      IotPage(iot: _iot),
      SettingsPage(controller: _apiController, onSave: _refreshAll),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Smart Classroom MVP'),
        actions: [
          IconButton(
            onPressed: _loading ? null : _refreshAll,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            if (_loading) const LinearProgressIndicator(),
            if (_error != null)
              MaterialBanner(
                content: Text(_error!),
                leading: const Icon(Icons.warning_amber_rounded),
                actions: [
                  TextButton(onPressed: _refreshAll, child: const Text('Retry')),
                ],
              ),
            Expanded(child: pages[_selectedIndex]),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.people), label: 'Students'),
          NavigationDestination(icon: Icon(Icons.event_note), label: 'Sessions'),
          NavigationDestination(icon: Icon(Icons.memory), label: 'IoT'),
          NavigationDestination(icon: Icon(Icons.settings), label: 'Settings'),
        ],
      ),
    );
  }
}

class DashboardPage extends StatelessWidget {
  const DashboardPage({super.key, required this.summary, required this.iot});

  final Map<String, dynamic>? summary;
  final Map<String, dynamic>? iot;

  @override
  Widget build(BuildContext context) {
    if (summary == null) {
      return const Center(child: Text('Tap refresh to load dashboard data.'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            StatCard(title: 'Students', value: '${summary!['student_count'] ?? 0}'),
            StatCard(title: 'Active Students', value: '${summary!['active_student_count'] ?? 0}'),
            StatCard(title: 'Classes', value: '${summary!['class_count'] ?? 0}'),
            StatCard(title: 'Today Sessions', value: '${summary!['today_session_count'] ?? 0}'),
          ],
        ),
        const SizedBox(height: 16),
        InfoCard(
          title: 'Raspberry Pi',
          lines: [
            'Status: ${summary!['raspberry_pi_status'] ?? 'Unknown'}',
            'Online: ${summary!['raspberry_pi_online'] == true ? 'Yes' : 'No'}',
            'Snapshot: ${summary!['latest_snapshot_available'] == true ? 'Available' : 'Unavailable'}',
            'Uploaded: ${summary!['latest_snapshot_uploaded_at'] ?? 'N/A'}',
          ],
        ),
        const SizedBox(height: 12),
        InfoCard(
          title: 'AI / IoT',
          lines: [
            'AI Analysis: ${summary!['ai_analysis_available'] == true ? 'Available' : 'Waiting'}',
            'Session Sync: ${summary!['session_sync_status'] ?? 'N/A'}',
            'Light 1: ${summary!['light_1_label'] ?? 'N/A'}',
            'Light 2: ${summary!['light_2_label'] ?? 'N/A'}',
          ],
        ),
      ],
    );
  }
}

class StudentsPage extends StatelessWidget {
  const StudentsPage({super.key, required this.students});

  final List<dynamic> students;

  @override
  Widget build(BuildContext context) {
    if (students.isEmpty) {
      return const Center(child: Text('No students loaded yet.'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: students.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final student = students[index] as Map<String, dynamic>;
        final classGroup = student['class_group'] as Map<String, dynamic>?;
        return Card(
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.person)),
            title: Text('${student['student_code']} - ${student['full_name']}'),
            subtitle: Text(classGroup == null ? 'No active class' : '${classGroup['class_code']} • ${classGroup['name']}'),
            trailing: Text('${student['status']}'),
          ),
        );
      },
    );
  }
}

class SessionsPage extends StatelessWidget {
  const SessionsPage({super.key, required this.sessions});

  final List<dynamic> sessions;

  @override
  Widget build(BuildContext context) {
    if (sessions.isEmpty) {
      return const Center(child: Text('No sessions for today.'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: sessions.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final session = sessions[index] as Map<String, dynamic>;
        final subject = session['subject'] as Map<String, dynamic>?;
        final classGroup = session['class_group'] as Map<String, dynamic>?;
        return Card(
          child: ListTile(
            leading: const Icon(Icons.event_available),
            title: Text(subject?['name']?.toString() ?? session['title'].toString()),
            subtitle: Text('${session['start_time']} - ${session['end_time']} • ${classGroup?['class_code'] ?? 'Class'} • ${session['room']}'),
            trailing: Chip(label: Text('${session['status']}')),
          ),
        );
      },
    );
  }
}

class IotPage extends StatelessWidget {
  const IotPage({super.key, required this.iot});

  final Map<String, dynamic>? iot;

  @override
  Widget build(BuildContext context) {
    if (iot == null) {
      return const Center(child: Text('No IoT status loaded yet.'));
    }
    final device = iot!['device'] as Map<String, dynamic>? ?? {};
    final snapshot = iot!['snapshot'] as Map<String, dynamic>? ?? {};
    final analysis = iot!['analysis_state'] as Map<String, dynamic>? ?? {};
    final light = iot!['light'] as Map<String, dynamic>? ?? {};

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        InfoCard(
          title: 'Device',
          lines: [
            'Name: ${device['device_name'] ?? 'Raspberry Pi'}',
            'Status: ${device['status_label'] ?? device['status'] ?? 'Unknown'}',
            'Source: ${device['status_source'] ?? 'N/A'}',
            'IP: ${device['ip_address'] ?? 'N/A'}',
          ],
        ),
        const SizedBox(height: 12),
        InfoCard(
          title: 'Snapshot',
          lines: [
            'Available: ${snapshot['available'] == true ? 'Yes' : 'No'}',
            'File: ${snapshot['filename'] ?? 'N/A'}',
            'Uploaded: ${snapshot['uploaded_at'] ?? 'N/A'}',
          ],
        ),
        const SizedBox(height: 12),
        InfoCard(
          title: 'AI Analysis',
          lines: [
            'Available: ${analysis['available'] == true ? 'Yes' : 'No'}',
            'Analyzed: ${analysis['analyzed_at'] ?? 'N/A'}',
            'Session Sync: ${analysis['session_sync_status'] ?? 'N/A'}',
          ],
        ),
        const SizedBox(height: 12),
        InfoCard(
          title: 'Lights',
          lines: [
            'Light 1: ${light['light_1_label'] ?? 'N/A'}',
            'Light 2: ${light['light_2_label'] ?? 'N/A'}',
          ],
        ),
      ],
    );
  }
}

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, required this.controller, required this.onSave});

  final TextEditingController controller;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text('Backend API URL', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: 'http://10.158.139.199:8000 or ngrok URL',
          ),
          keyboardType: TextInputType.url,
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: onSave,
          icon: const Icon(Icons.check),
          label: const Text('Save and Refresh'),
        ),
        const SizedBox(height: 16),
        const Text(
          'Android phone cannot use 127.0.0.1 for your laptop backend. Use your laptop WiFi IP or an ngrok HTTPS URL.',
        ),
      ],
    );
  }
}

class StatCard extends StatelessWidget {
  const StatCard({super.key, required this.title, required this.value});

  final String title;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 160,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: 8),
              Text(value, style: Theme.of(context).textTheme.headlineMedium),
            ],
          ),
        ),
      ),
    );
  }
}

class InfoCard extends StatelessWidget {
  const InfoCard({super.key, required this.title, required this.lines});

  final String title;
  final List<String> lines;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            for (final line in lines) Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(line),
            ),
          ],
        ),
      ),
    );
  }
}



