import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../core/models/location.dart';
import '../../../core/models/report.dart';

class ReportsTab extends StatefulWidget {
  const ReportsTab({super.key});

  @override
  State<ReportsTab> createState() => _ReportsTabState();
}

class _ReportsTabState extends State<ReportsTab> {
  List<Location> _locations = [];
  String? _locationId;

  @override
  void initState() {
    super.initState();
    _loadLocations();
  }

  Future<void> _loadLocations() async {
    try {
      final data = await ApiClient.instance.get('/locations') as List;
      final locations = data
          .map((e) => Location.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() {
        _locations = locations;
        if (locations.isNotEmpty) _locationId = locations.first.id;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        DropdownButtonFormField<String>(
          initialValue: _locationId,
          decoration: const InputDecoration(labelText: 'Location'),
          items: _locations
              .map((l) => DropdownMenuItem(value: l.id, child: Text(l.name)))
              .toList(),
          onChanged: (value) => setState(() => _locationId = value),
        ),
        const SizedBox(height: 16),
        if (_locationId != null) _LocationReports(locationId: _locationId!),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Audit log',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                const _AuditLogView(),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _LocationReports extends StatefulWidget {
  final String locationId;

  const _LocationReports({required this.locationId});

  @override
  State<_LocationReports> createState() => _LocationReportsState();
}

class _LocationReportsState extends State<_LocationReports> {
  SalesSummary? _summary;
  ReconciliationReport? _reconciliation;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant _LocationReports oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.locationId != widget.locationId) _load();
  }

  Future<void> _load() async {
    setState(() {
      _summary = null;
      _reconciliation = null;
    });
    try {
      final summaryData = await ApiClient.instance.get(
        '/reports/locations/${widget.locationId}/sales-summary',
      );
      if (mounted) {
        setState(
          () => _summary = SalesSummary.fromJson(
            summaryData as Map<String, dynamic>,
          ),
        );
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
    try {
      final reconciliationData = await ApiClient.instance.get(
        '/reports/locations/${widget.locationId}/reconciliation',
      );
      if (mounted) {
        setState(
          () => _reconciliation = ReconciliationReport.fromJson(
            reconciliationData as Map<String, dynamic>,
          ),
        );
      }
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final summary = _summary;
    final reconciliation = _reconciliation;
    return Column(
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Sales summary (last 30 days)',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                if (summary == null)
                  const Center(child: CircularProgressIndicator())
                else
                  Wrap(
                    spacing: 24,
                    runSpacing: 12,
                    children: [
                      _Stat(
                        label: 'Total orders',
                        value: '${summary.totalOrders}',
                      ),
                      _Stat(label: 'Revenue', value: summary.totalRevenue),
                      _Stat(
                        label: 'By status',
                        value: summary.ordersByStatus.entries
                            .map((e) => '${e.key}: ${e.value}')
                            .join(', '),
                      ),
                      _Stat(
                        label: 'By type',
                        value: summary.ordersByType.entries
                            .map((e) => '${e.key}: ${e.value}')
                            .join(', '),
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      'Reconciliation',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(width: 8),
                    if (reconciliation != null)
                      Chip(
                        label: Text(
                          '${reconciliation.mismatchCount} mismatch(es)',
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                if (reconciliation == null)
                  const Center(child: CircularProgressIndicator())
                else if (reconciliation.lines.isEmpty)
                  const Text('No served items in this period.')
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('Order')),
                        DataColumn(label: Text('Served / Ordered')),
                        DataColumn(label: Text('Expected')),
                        DataColumn(label: Text('Billed')),
                        DataColumn(label: Text('Match')),
                      ],
                      rows: [
                        for (final line in reconciliation.lines)
                          DataRow(
                            cells: [
                              DataCell(Text(line.orderNumber)),
                              DataCell(
                                Text(
                                  '${line.servedQuantity} / ${line.orderedQuantity}',
                                ),
                              ),
                              DataCell(Text(line.expectedAmount)),
                              DataCell(Text(line.billedAmount)),
                              DataCell(Text(line.matches ? 'OK' : 'Mismatch')),
                            ],
                          ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _Stat extends StatelessWidget {
  final String label;
  final String value;

  const _Stat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.bodySmall),
        Text(value, style: Theme.of(context).textTheme.titleSmall),
      ],
    );
  }
}

class _AuditLogView extends StatefulWidget {
  const _AuditLogView();

  @override
  State<_AuditLogView> createState() => _AuditLogViewState();
}

class _AuditLogViewState extends State<_AuditLogView> {
  List<AuditLogEntry>? _entries;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ApiClient.instance.get('/reports/audit-log') as List;
      final entries = data
          .map((e) => AuditLogEntry.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _entries = entries);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final entries = _entries;
    if (entries == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final limited = entries.take(100).toList();
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('When')),
          DataColumn(label: Text('Action')),
          DataColumn(label: Text('Entity')),
        ],
        rows: [
          for (final entry in limited)
            DataRow(
              cells: [
                DataCell(
                  Text(DateTime.parse(entry.createdAt).toLocal().toString()),
                ),
                DataCell(Text(entry.action)),
                DataCell(
                  Text(
                    '${entry.entityType} ${entry.entityId != null ? '#${entry.entityId!.substring(0, 8)}' : ''}',
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
