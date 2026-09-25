import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../core/models/employee.dart';
import '../../../core/models/location.dart';

// Mirrors MANAGER_ELIGIBLE_ROLES in
// backend/app/services/locations/location_service.py.
const _managerEligibleRoles = [
  'LOCATION_MANAGER',
  'SYSTEM_MANAGER',
  'SYSTEM_ADMINISTRATOR',
];

class LocationsTab extends StatefulWidget {
  const LocationsTab({super.key});

  @override
  State<LocationsTab> createState() => _LocationsTabState();
}

class _LocationsTabState extends State<LocationsTab> {
  List<Location>? _locations;
  List<Employee> _eligibleManagers = [];

  @override
  void initState() {
    super.initState();
    _load();
    _loadManagers();
  }

  Future<void> _load() async {
    try {
      final data = await ApiClient.instance.get('/locations') as List;
      final locations = data
          .map((e) => Location.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _locations = locations);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _loadManagers() async {
    try {
      final data =
          await ApiClient.instance.get(
                '/employees',
                query: {'role': _managerEligibleRoles},
              )
              as List;
      final managers = data
          .map((e) => Employee.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _eligibleManagers = managers);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final locations = _locations;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _CreateLocationForm(onCreated: _load),
        const SizedBox(height: 16),
        if (locations == null)
          const Center(child: CircularProgressIndicator())
        else
          for (final location in locations)
            _LocationCard(
              location: location,
              eligibleManagers: _eligibleManagers,
            ),
      ],
    );
  }
}

class _CreateLocationForm extends StatefulWidget {
  final VoidCallback onCreated;

  const _CreateLocationForm({required this.onCreated});

  @override
  State<_CreateLocationForm> createState() => _CreateLocationFormState();
}

class _CreateLocationFormState extends State<_CreateLocationForm> {
  final _nameController = TextEditingController();
  final _codeController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      await ApiClient.instance.post(
        '/locations',
        body: {'name': _nameController.text, 'code': _codeController.text},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Location created')));
      _nameController.clear();
      _codeController.clear();
      widget.onCreated();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Create location',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Name'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _codeController,
              decoration: const InputDecoration(labelText: 'Code'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed:
                  _submitting ||
                      _nameController.text.isEmpty ||
                      _codeController.text.isEmpty
                  ? null
                  : _submit,
              child: _submitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }
}

class _LocationCard extends StatefulWidget {
  final Location location;
  final List<Employee> eligibleManagers;

  const _LocationCard({required this.location, required this.eligibleManagers});

  @override
  State<_LocationCard> createState() => _LocationCardState();
}

class _LocationCardState extends State<_LocationCard> {
  List<KitchenStation>? _stations;
  final _newStationController = TextEditingController();
  String? _managerId;
  bool _assigning = false;

  @override
  void initState() {
    super.initState();
    _loadStations();
  }

  @override
  void dispose() {
    _newStationController.dispose();
    super.dispose();
  }

  Future<void> _loadStations() async {
    try {
      final data =
          await ApiClient.instance.get(
                '/locations/${widget.location.id}/kitchen-stations',
              )
              as List;
      final stations = data
          .map((e) => KitchenStation.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _stations = stations);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _addStation() async {
    try {
      await ApiClient.instance.post(
        '/locations/${widget.location.id}/kitchen-stations',
        body: {'name': _newStationController.text},
      );
      _newStationController.clear();
      _loadStations();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _assignManager() async {
    if (_managerId == null) return;
    setState(() => _assigning = true);
    try {
      await ApiClient.instance.patch(
        '/locations/${widget.location.id}',
        body: {'manager_id': _managerId},
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Manager assigned')));
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _assigning = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    Employee? currentManager;
    for (final emp in widget.eligibleManagers) {
      if (emp.id == widget.location.managerId) {
        currentManager = emp;
        break;
      }
    }

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    '${widget.location.name} (${widget.location.code})',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                Chip(label: Text(widget.location.status)),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              currentManager != null
                  ? 'Manager — currently ${currentManager.name}'
                  : 'Manager',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _managerId,
                    decoration: const InputDecoration(
                      hintText: 'Choose an eligible employee',
                    ),
                    items: widget.eligibleManagers
                        .map(
                          (emp) => DropdownMenuItem(
                            value: emp.id,
                            child: Text(
                              '${emp.name} (${emp.pNo}) — ${emp.role}',
                            ),
                          ),
                        )
                        .toList(),
                    onChanged: (value) => setState(() => _managerId = value),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _managerId == null || _assigning
                      ? null
                      : _assignManager,
                  child: const Text('Assign'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Kitchen stations',
              style: Theme.of(context).textTheme.labelMedium,
            ),
            if (_stations == null)
              const Center(child: CircularProgressIndicator())
            else
              for (final station in _stations!) Text('• ${station.name}'),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _newStationController,
                    decoration: const InputDecoration(hintText: 'Station name'),
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _newStationController.text.isEmpty
                      ? null
                      : _addStation,
                  child: const Text('Add'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
