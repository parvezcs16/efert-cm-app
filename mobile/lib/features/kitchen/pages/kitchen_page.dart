import 'dart:async';

import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../core/api_client.dart';
import '../../../core/auth_storage.dart';
import '../../../core/models/location.dart';
import '../../../core/models/order.dart';
import '../../../core/ws.dart';

const _nextAction = {
  'PENDING': ('Confirm', 'confirm'),
  'PREPARING': ('Mark ready', 'mark-ready'),
  'READY': ('Serve', 'serve'),
};

class KitchenPage extends StatefulWidget {
  const KitchenPage({super.key});

  @override
  State<KitchenPage> createState() => _KitchenPageState();
}

class _KitchenPageState extends State<KitchenPage> {
  final _api = ApiClient.instance;
  final _authStorage = EmployeeAuthStorage();

  List<Location> _locations = [];
  String _locationId = '';
  List<KitchenStation> _stations = [];
  String _stationId = '';
  List<Order> _incoming = [];
  List<Order> _queue = [];
  List<Order> _pendingBookings = [];
  bool _loading = false;
  String? _error;
  WebSocketChannel? _channel;

  @override
  void initState() {
    super.initState();
    _loadLocations();
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  Future<void> _loadLocations() async {
    try {
      final data = await _api.get('/locations') as List;
      final all = data
          .map((e) => Location.fromJson(e as Map<String, dynamic>))
          .toList();
      final active = all.where((l) => l.status == 'ACTIVE').toList();
      if (!mounted) return;
      setState(() => _locations = active);
      if (active.isNotEmpty) _selectLocation(active.first.id);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  Future<void> _selectLocation(String locationId) async {
    setState(() => _locationId = locationId);
    await _loadStations();
    await _refresh();
    _connectSocket();
  }

  Future<void> _loadStations() async {
    try {
      final data =
          await _api.get('/locations/$_locationId/kitchen-stations') as List;
      final all = data
          .map((e) => KitchenStation.fromJson(e as Map<String, dynamic>))
          .toList();
      final active = all.where((s) => s.status == 'ACTIVE').toList();
      if (!mounted) return;
      setState(() {
        _stations = active;
        if (!active.any((s) => s.id == _stationId)) {
          _stationId = active.isNotEmpty ? active.first.id : '';
        }
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  Future<void> _refresh() async {
    if (_locationId.isEmpty) return;
    setState(() => _loading = true);
    try {
      final incomingData =
          await _api.get('/locations/$_locationId/orders/incoming') as List;
      final bookingsData =
          await _api.get('/locations/$_locationId/bookings/pending') as List;
      List<Order> queueData = [];
      if (_stationId.isNotEmpty) {
        final data =
            await _api.get(
                  '/locations/$_locationId/kitchen-stations/$_stationId/queue',
                )
                as List;
        queueData = data
            .map((e) => Order.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      if (!mounted) return;
      setState(() {
        _incoming = incomingData
            .map((e) => Order.fromJson(e as Map<String, dynamic>))
            .toList();
        _pendingBookings = bookingsData
            .map((e) => Order.fromJson(e as Map<String, dynamic>))
            .toList();
        _queue = queueData;
        _error = null;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _connectSocket() async {
    _channel?.sink.close();
    final token = await _authStorage.getAccessToken();
    if (token == null || _locationId.isEmpty) return;
    final channel = WebSocketChannel.connect(
      Uri.parse(kitchenSocketUrl(_locationId, token)),
    );
    _channel = channel;
    channel.stream.listen(
      (_) => _refresh(),
      onError: (_) {
        // Live updates simply stop; manual pull-to-refresh still works.
      },
      cancelOnError: false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _locationId.isEmpty ? null : _locationId,
                  decoration: const InputDecoration(labelText: 'Location'),
                  items: _locations
                      .map(
                        (l) =>
                            DropdownMenuItem(value: l.id, child: Text(l.name)),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) _selectLocation(value);
                  },
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _stationId.isEmpty ? null : _stationId,
                  decoration: const InputDecoration(labelText: 'Station'),
                  items: _stations
                      .map(
                        (s) =>
                            DropdownMenuItem(value: s.id, child: Text(s.name)),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) {
                      setState(() => _stationId = value);
                      _refresh();
                    }
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_loading && _incoming.isEmpty && _queue.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            )
          else ...[
            if (_pendingBookings.isNotEmpty) ...[
              Text(
                'Booked orders awaiting review',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              for (final order in _pendingBookings)
                _OrderCard(
                  order: order,
                  stationId: _stationId,
                  onRefresh: _refresh,
                ),
              const SizedBox(height: 16),
            ],
            Text('Incoming', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            if (_incoming.isEmpty)
              const Text('Nothing waiting on confirm/queue.'),
            for (final order in _incoming)
              _OrderCard(
                order: order,
                stationId: _stationId,
                onRefresh: _refresh,
              ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Station queue',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 8),
                    if (_queue.isEmpty) const Text('Queue is empty.'),
                    for (final order in _queue)
                      _OrderCard(
                        order: order,
                        stationId: _stationId,
                        onRefresh: _refresh,
                      ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _OrderCard extends StatefulWidget {
  final Order order;
  final String stationId;
  final VoidCallback onRefresh;

  const _OrderCard({
    required this.order,
    required this.stationId,
    required this.onRefresh,
  });

  @override
  State<_OrderCard> createState() => _OrderCardState();
}

class _OrderCardState extends State<_OrderCard> {
  bool _busy = false;
  bool _showDelay = false;
  final _delayReasonController = TextEditingController();

  @override
  void dispose() {
    _delayReasonController.dispose();
    super.dispose();
  }

  Future<void> _runAction(String path, {Map<String, dynamic>? body}) async {
    setState(() => _busy = true);
    try {
      await ApiClient.instance.post(path, body: body);
      widget.onRefresh();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirmIngredients() =>
      _runAction('/orders/${widget.order.id}/booking/confirm-ingredients');

  Future<void> _submitDelay() async {
    final newTime = DateTime.now()
        .add(const Duration(hours: 1))
        .toIso8601String();
    await _runAction(
      '/orders/${widget.order.id}/booking/delay',
      body: {
        'new_scheduled_for': newTime,
        'reason': _delayReasonController.text,
      },
    );
    if (mounted) setState(() => _showDelay = false);
  }

  void _handleQueue() {
    if (widget.stationId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Select a kitchen station first')),
      );
      return;
    }
    final assignments = {
      for (final item in widget.order.items) item.id: widget.stationId,
    };
    _runAction(
      '/orders/${widget.order.id}/queue',
      body: {'station_assignments': assignments},
    );
  }

  @override
  Widget build(BuildContext context) {
    final order = widget.order;
    final next = _nextAction[order.status];
    final needsBookingReview =
        order.orderType == 'BOOK_FOR_LATER' &&
        order.ingredientStatus != 'CONFIRMED';
    final itemCount = order.items.fold(0, (sum, i) => sum + i.orderedQuantity);

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
                Text(
                  order.orderNumber,
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                Row(
                  children: [
                    Chip(label: Text(order.orderType.replaceAll('_', ' '))),
                    const SizedBox(width: 4),
                    Chip(label: Text(order.status)),
                  ],
                ),
              ],
            ),
            Text(
              '$itemCount item(s)',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            if (needsBookingReview)
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.amber),
                  borderRadius: BorderRadius.circular(6),
                  color: Colors.amber.withValues(alpha: 0.1),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Ingredients need review before ${order.scheduledFor}',
                    ),
                    const SizedBox(height: 8),
                    if (_showDelay) ...[
                      TextField(
                        controller: _delayReasonController,
                        decoration: const InputDecoration(
                          hintText: 'Reason for delay',
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        children: [
                          FilledButton(
                            onPressed:
                                _busy || _delayReasonController.text.isEmpty
                                ? null
                                : _submitDelay,
                            child: const Text('Send delay'),
                          ),
                          TextButton(
                            onPressed: () => setState(() => _showDelay = false),
                            child: const Text('Cancel'),
                          ),
                        ],
                      ),
                    ] else
                      Wrap(
                        spacing: 8,
                        children: [
                          FilledButton(
                            onPressed: _busy ? null : _confirmIngredients,
                            child: const Text('Confirm available'),
                          ),
                          OutlinedButton(
                            onPressed: _busy
                                ? null
                                : () => setState(() => _showDelay = true),
                            child: const Text('Delay'),
                          ),
                        ],
                      ),
                  ],
                ),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (order.status == 'CONFIRMED')
                    FilledButton(
                      onPressed: _busy ? null : _handleQueue,
                      child: const Text('Queue to station'),
                    ),
                  if (order.status == 'QUEUED')
                    FilledButton(
                      onPressed: _busy
                          ? null
                          : () => _runAction(
                              '/orders/${order.id}/start-preparing',
                            ),
                      child: const Text('Start preparing'),
                    ),
                  if (next != null)
                    FilledButton(
                      onPressed: _busy
                          ? null
                          : () => _runAction('/orders/${order.id}/${next.$2}'),
                      child: Text(next.$1),
                    ),
                  if (order.status != 'SERVED' && order.status != 'CANCELLED')
                    OutlinedButton(
                      onPressed: _busy
                          ? null
                          : () => _runAction(
                              '/orders/${order.id}/serve-directly',
                            ),
                      child: const Text('Serve directly'),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}
