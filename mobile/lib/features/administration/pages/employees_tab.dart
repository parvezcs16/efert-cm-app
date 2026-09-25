import 'package:flutter/material.dart';

import '../../../core/api_client.dart';
import '../../../core/models/employee.dart';

class _PendingRegistration {
  final String id;
  final String pNo;
  final String email;
  final String name;

  _PendingRegistration({
    required this.id,
    required this.pNo,
    required this.email,
    required this.name,
  });

  factory _PendingRegistration.fromJson(Map<String, dynamic> json) =>
      _PendingRegistration(
        id: json['id'] as String,
        pNo: json['p_no'] as String,
        email: json['email'] as String,
        name: json['name'] as String,
      );
}

class EmployeesTab extends StatefulWidget {
  const EmployeesTab({super.key});

  @override
  State<EmployeesTab> createState() => _EmployeesTabState();
}

class _EmployeesTabState extends State<EmployeesTab> {
  List<_PendingRegistration>? _pending;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ApiClient.instance.get('/auth/registrations') as List;
      final pending = data
          .map((e) => _PendingRegistration.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _pending = pending);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _decide(String id, String decision) async {
    try {
      await ApiClient.instance.post(
        '/auth/registrations/$id/$decision',
        body: decision == 'reject' ? {} : null,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Registration ${decision}d')));
      _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final pending = _pending;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _CreateEmployeeForm(),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Pending registrations',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                if (pending == null)
                  const Center(child: CircularProgressIndicator())
                else if (pending.isEmpty)
                  const Text('No pending registrations.')
                else
                  for (final reg in pending)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${reg.name} (${reg.pNo}) — ${reg.email}'),
                          const SizedBox(height: 4),
                          Wrap(
                            spacing: 8,
                            children: [
                              FilledButton(
                                onPressed: () => _decide(reg.id, 'approve'),
                                child: const Text('Approve'),
                              ),
                              OutlinedButton(
                                onPressed: () => _decide(reg.id, 'reject'),
                                child: const Text('Reject'),
                              ),
                            ],
                          ),
                          const Divider(),
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

class _CreateEmployeeForm extends StatefulWidget {
  @override
  State<_CreateEmployeeForm> createState() => _CreateEmployeeFormState();
}

class _CreateEmployeeFormState extends State<_CreateEmployeeForm> {
  final _pNoController = TextEditingController();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  String _role = 'EMPLOYEE';
  bool _submitting = false;

  @override
  void dispose() {
    _pNoController.dispose();
    _nameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _pNoController.text.isNotEmpty &&
      _nameController.text.isNotEmpty &&
      _emailController.text.isNotEmpty;

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      await ApiClient.instance.post(
        '/employees',
        body: {
          'p_no': _pNoController.text,
          'name': _nameController.text,
          'email': _emailController.text,
          'role': _role,
        },
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Employee created — credentials emailed')),
      );
      _pNoController.clear();
      _nameController.clear();
      _emailController.clear();
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
              'Create employee',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pNoController,
              decoration: const InputDecoration(labelText: 'P-Number'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Name'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: 'Email'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _role,
              decoration: const InputDecoration(labelText: 'Role'),
              items: employeeRoles
                  .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                  .toList(),
              onChanged: (value) {
                if (value != null) setState(() => _role = value);
              },
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _submitting || !_canSubmit ? null : _submit,
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
