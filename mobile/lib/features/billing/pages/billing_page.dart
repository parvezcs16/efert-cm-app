import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/api_client.dart';
import '../../../core/models/billing.dart';
import '../../auth/auth_controller.dart';

const _tabs = [
  ('personal', 'Personal', '/billing/me/personal'),
  ('private-guests', 'Private guests', '/billing/me/private-guests'),
  ('consolidated', 'Consolidated', '/billing/me/consolidated'),
];

class BillingPage extends StatefulWidget {
  const BillingPage({super.key});

  @override
  State<BillingPage> createState() => _BillingPageState();
}

class _BillingPageState extends State<BillingPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  bool _updatingFrequency = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _changeFrequency(String frequency) async {
    setState(() => _updatingFrequency = true);
    try {
      await ApiClient.instance.patch(
        '/employees/me/statement-frequency',
        body: {'frequency': frequency},
      );
      if (!mounted) return;
      await context.read<AuthController>().refreshProfile();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Statement frequency updated')),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _updatingFrequency = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final employee = context.watch<AuthController>().employee;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Text('Email me a statement'),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      initialValue: employee?.statementFrequency,
                      items: statementFrequencies
                          .map(
                            (f) => DropdownMenuItem(value: f, child: Text(f)),
                          )
                          .toList(),
                      onChanged: _updatingFrequency
                          ? null
                          : (value) {
                              if (value != null) _changeFrequency(value);
                            },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        TabBar(
          controller: _tabController,
          tabs: [for (final tab in _tabs) Tab(text: tab.$2)],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: [for (final tab in _tabs) _StatementView(path: tab.$3)],
          ),
        ),
      ],
    );
  }
}

class _StatementView extends StatefulWidget {
  final String path;

  const _StatementView({required this.path});

  @override
  State<_StatementView> createState() => _StatementViewState();
}

class _StatementViewState extends State<_StatementView> {
  Statement? _statement;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ApiClient.instance.get(widget.path);
      final statement = Statement.fromJson(data as Map<String, dynamic>);
      if (!mounted) return;
      setState(() => _statement = statement);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final statement = _statement;
    if (statement == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            Expanded(
              child: _SummaryCard(
                label: 'Charges',
                value: statement.totalDebit,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _SummaryCard(
                label: 'Credits',
                value: statement.totalCredit,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _SummaryCard(
                label: 'Net balance',
                value: statement.netBalance,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (statement.entries.isEmpty)
          const Text('No activity yet.')
        else
          Card(
            child: Column(
              children: [
                for (final entry in statement.entries)
                  ListTile(
                    title: Text(entry.reason),
                    subtitle: Text(
                      DateTime.parse(
                        entry.createdAt,
                      ).toLocal().toString().substring(0, 10),
                    ),
                    leading: Chip(label: Text(entry.entryType)),
                    trailing: Text(entry.amount),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final String label;
  final String value;

  const _SummaryCard({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Text(label, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 4),
            Text(value, style: Theme.of(context).textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}
