import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../../../core/models/location.dart';
import '../../../core/models/menu.dart';
import '../../../core/models/order.dart';

const _orderTypes = [
  ('DINE_IN', 'Dine in'),
  ('TAKEAWAY', 'Takeaway'),
  ('BOOK_FOR_LATER', 'Book for later'),
];

class OrderingPage extends StatefulWidget {
  const OrderingPage({super.key});

  @override
  State<OrderingPage> createState() => _OrderingPageState();
}

class _OrderingPageState extends State<OrderingPage> {
  final _api = ApiClient.instance;

  List<Location> _locations = [];
  String? _locationId;
  List<MenuBrowseCategory> _categories = [];
  bool _menuLoading = false;
  final Map<String, int> _cart = {};
  String _orderType = 'DINE_IN';
  DateTime? _scheduledFor;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadLocations();
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
    setState(() {
      _locationId = locationId;
      _menuLoading = true;
      _cart.clear();
    });
    try {
      final data = await _api.get('/locations/$locationId/menu/browse') as List;
      final categories = data
          .map((e) => MenuBrowseCategory.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _categories = categories);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _menuLoading = false);
    }
  }

  int get _itemCount => _cart.values.fold(0, (sum, q) => sum + q);

  void _adjustCart(String itemId, int delta) {
    setState(() {
      final updated = (_cart[itemId] ?? 0) + delta;
      if (updated <= 0) {
        _cart.remove(itemId);
      } else {
        _cart[itemId] = updated;
      }
    });
  }

  Future<void> _submit() async {
    if (_itemCount == 0) {
      setState(() => _error = 'Add at least one item to your order');
      return;
    }
    if (_orderType == 'BOOK_FOR_LATER' && _scheduledFor == null) {
      setState(() => _error = 'Choose a time for your booking');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final response = await _api.post(
        '/orders',
        body: {
          'location_id': _locationId,
          'order_type': _orderType,
          'scheduled_for': _orderType == 'BOOK_FOR_LATER'
              ? _scheduledFor!.toIso8601String()
              : null,
          'items': _cart.entries
              .map((e) => {'menu_item_id': e.key, 'quantity': e.value})
              .toList(),
        },
      );
      final order = Order.fromJson(response as Map<String, dynamic>);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Order ${order.orderNumber} placed')),
      );
      context.push('/orders/${order.id}');
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _pickScheduledFor() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: _scheduledFor ?? now,
      firstDate: now,
      lastDate: now.add(const Duration(days: 30)),
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_scheduledFor ?? now),
    );
    if (time == null) return;
    setState(() {
      _scheduledFor = DateTime(
        date.year,
        date.month,
        date.day,
        time.hour,
        time.minute,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _loadLocations,
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
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Place an order',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: _locationId,
                    decoration: const InputDecoration(labelText: 'Location'),
                    items: _locations
                        .map(
                          (l) => DropdownMenuItem(
                            value: l.id,
                            child: Text(l.name),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) _selectLocation(value);
                    },
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _orderType,
                    decoration: const InputDecoration(labelText: 'Order type'),
                    items: _orderTypes
                        .map(
                          (t) =>
                              DropdownMenuItem(value: t.$1, child: Text(t.$2)),
                        )
                        .toList(),
                    onChanged: (value) {
                      if (value != null) setState(() => _orderType = value);
                    },
                  ),
                  if (_orderType == 'BOOK_FOR_LATER') ...[
                    const SizedBox(height: 12),
                    OutlinedButton(
                      onPressed: _pickScheduledFor,
                      child: Text(
                        _scheduledFor == null
                            ? 'Choose serving time'
                            : _scheduledFor.toString().substring(0, 16),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (_menuLoading)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_categories.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(
                child: Text('No items available at this location right now.'),
              ),
            )
          else
            for (final category in _categories) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        category.name,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      const SizedBox(height: 8),
                      for (final item in category.items)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 6),
                          child: Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(item.name),
                                    if (item.description != null)
                                      Text(
                                        item.description!,
                                        style: Theme.of(
                                          context,
                                        ).textTheme.bodySmall,
                                      ),
                                  ],
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.remove_circle_outline),
                                onPressed: (_cart[item.id] ?? 0) > 0
                                    ? () => _adjustCart(item.id, -1)
                                    : null,
                              ),
                              SizedBox(
                                width: 24,
                                child: Text(
                                  '${_cart[item.id] ?? 0}',
                                  textAlign: TextAlign.center,
                                ),
                              ),
                              IconButton(
                                icon: const Icon(Icons.add_circle_outline),
                                onPressed: () => _adjustCart(item.id, 1),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),
            ],
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _submitting || _itemCount == 0 ? null : _submit,
            icon: _submitting
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.shopping_cart),
            label: Text('Place order ($_itemCount)'),
          ),
        ],
      ),
    );
  }
}
