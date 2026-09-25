import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../../core/api_client.dart';
import '../../../core/models/guest.dart';

const _guestTypes = [('PRIVATE', 'Private'), ('OFFICIAL', 'Official')];

class GuestsPage extends StatefulWidget {
  const GuestsPage({super.key});

  @override
  State<GuestsPage> createState() => _GuestsPageState();
}

class _GuestsPageState extends State<GuestsPage> {
  List<Guest>? _guests;

  @override
  void initState() {
    super.initState();
    _loadGuests();
  }

  Future<void> _loadGuests() async {
    try {
      final data = await ApiClient.instance.get('/guests') as List;
      final guests = data
          .map((e) => Guest.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _guests = guests);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final guests = _guests;
    return RefreshIndicator(
      onRefresh: _loadGuests,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _RegisterGuestForm(onRegistered: _loadGuests),
          const SizedBox(height: 16),
          Text('Your guests', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          if (guests == null)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (guests.isEmpty)
            const Text('No guests registered yet.')
          else
            for (final guest in guests)
              _GuestRow(guest: guest, onChanged: _loadGuests),
        ],
      ),
    );
  }
}

class _RegisterGuestForm extends StatefulWidget {
  final VoidCallback onRegistered;

  const _RegisterGuestForm({required this.onRegistered});

  @override
  State<_RegisterGuestForm> createState() => _RegisterGuestFormState();
}

class _RegisterGuestFormState extends State<_RegisterGuestForm> {
  final _nameController = TextEditingController();
  final _companyController = TextEditingController();
  final _cnicController = TextEditingController();
  final _accompanyingController = TextEditingController(text: '0');
  String _guestType = 'PRIVATE';
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _companyController.dispose();
    _cnicController.dispose();
    _accompanyingController.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _nameController.text.isNotEmpty &&
      _companyController.text.isNotEmpty &&
      _cnicController.text.isNotEmpty;

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      await ApiClient.instance.post(
        '/guests',
        body: {
          'name': _nameController.text,
          'company_name': _companyController.text,
          'cnic': _cnicController.text,
          'guest_type': _guestType,
          'accompanying_persons':
              int.tryParse(_accompanyingController.text) ?? 0,
        },
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Guest registered')));
      _nameController.clear();
      _companyController.clear();
      _cnicController.clear();
      _accompanyingController.text = '0';
      widget.onRegistered();
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
              'Register a guest',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _nameController,
              decoration: const InputDecoration(labelText: 'Name'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _companyController,
              decoration: const InputDecoration(labelText: 'Company'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _cnicController,
              decoration: const InputDecoration(labelText: 'CNIC'),
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _guestType,
              decoration: const InputDecoration(labelText: 'Guest type'),
              items: _guestTypes
                  .map((t) => DropdownMenuItem(value: t.$1, child: Text(t.$2)))
                  .toList(),
              onChanged: (value) {
                if (value != null) setState(() => _guestType = value);
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _accompanyingController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Accompanying persons',
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _submitting || !_canSubmit ? null : _submit,
              child: _submitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Register guest'),
            ),
          ],
        ),
      ),
    );
  }
}

class _GuestRow extends StatefulWidget {
  final Guest guest;
  final VoidCallback onChanged;

  const _GuestRow({required this.guest, required this.onChanged});

  @override
  State<_GuestRow> createState() => _GuestRowState();
}

class _GuestRowState extends State<_GuestRow> {
  List<GuestSession>? _sessions;
  bool _busy = false;

  Future<void> _loadSessions() async {
    try {
      final data =
          await ApiClient.instance.get('/guests/${widget.guest.id}/sessions')
              as List;
      final sessions = data
          .map((e) => GuestSession.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _sessions = sessions);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _openSession() async {
    setState(() => _busy = true);
    try {
      final data = await ApiClient.instance.post(
        '/guests/${widget.guest.id}/sessions',
      );
      final result = GuestSessionCreateResponse.fromJson(
        data as Map<String, dynamic>,
      );
      await _loadSessions();
      widget.onChanged();
      if (!mounted) return;
      _showQrDialog(result.qrToken);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _closeSession(String sessionId) async {
    setState(() => _busy = true);
    try {
      await ApiClient.instance.post('/guests/sessions/$sessionId/close');
      await _loadSessions();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reopenSession(String sessionId) async {
    setState(() => _busy = true);
    try {
      await ApiClient.instance.post('/guests/sessions/$sessionId/reopen');
      await _loadSessions();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showQrDialog(String token) {
    final url =
        '${ApiClient.webAppBaseUrl}/guest?token=${Uri.encodeComponent(token)}';
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Scan to order'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            QrImageView(data: url, size: 220),
            const SizedBox(height: 12),
            Text(
              url,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final sessions = _sessions;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.guest.name,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      Text(
                        '${widget.guest.companyName} · ${widget.guest.guestType}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                FilledButton(
                  onPressed: _busy ? null : _openSession,
                  child: const Text('New session'),
                ),
              ],
            ),
            TextButton(
              onPressed: _loadSessions,
              child: Text(
                sessions == null ? 'Show sessions' : 'Refresh sessions',
              ),
            ),
            if (sessions != null) ...[
              if (sessions.isEmpty) const Text('No sessions yet.'),
              for (final session in sessions)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Row(
                          children: [
                            Flexible(
                              child: Text(
                                DateTime.parse(
                                  session.openedAt,
                                ).toLocal().toString(),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Chip(label: Text(session.status)),
                          ],
                        ),
                      ),
                      if (session.status == 'ACTIVE')
                        OutlinedButton(
                          onPressed: _busy
                              ? null
                              : () => _closeSession(session.id),
                          child: const Text('Close'),
                        )
                      else
                        OutlinedButton(
                          onPressed: _busy
                              ? null
                              : () => _reopenSession(session.id),
                          child: const Text('Reopen'),
                        ),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
