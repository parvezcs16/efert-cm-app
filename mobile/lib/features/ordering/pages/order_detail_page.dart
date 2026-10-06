import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../../../core/models/order.dart';

// Mirrors EDITABLE_STATUSES in the backend order service: items can be
// changed until the kitchen queues the order.
const _editable = {'PENDING', 'CONFIRMED'};

class OrderDetailPage extends StatefulWidget {
  final String orderId;

  const OrderDetailPage({super.key, required this.orderId});

  @override
  State<OrderDetailPage> createState() => _OrderDetailPageState();
}

class _OrderDetailPageState extends State<OrderDetailPage> {
  Order? _order;
  final Map<String, ConsumptionRecord> _consumption = {};
  // Item id -> quantity to keep; items absent from the map are removed.
  Map<String, int> _draft = {};
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await ApiClient.instance.get('/orders/${widget.orderId}');
      final order = Order.fromJson(data as Map<String, dynamic>);
      if (!mounted) return;
      setState(() {
        _order = order;
        _resetDraft();
      });
      if (order.status == 'SERVED') _loadConsumption(order);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  void _resetDraft() {
    _draft = {
      for (final item in _order?.items ?? <OrderItem>[])
        item.id: item.orderedQuantity,
    };
  }

  bool get _dirty {
    final order = _order;
    if (order == null) return false;
    return order.items.any((i) => _draft[i.id] != i.orderedQuantity);
  }

  Future<void> _loadConsumption(Order order) async {
    for (final item in order.items) {
      try {
        final data = await ApiClient.instance.get(
          '/orders/${order.id}/items/${item.id}/consumption',
        );
        if (!mounted) return;
        setState(() {
          _consumption[item.id] = ConsumptionRecord.fromJson(
            data as Map<String, dynamic>,
          );
        });
      } on ApiException {
        // Not yet served / no record -- fine to leave unset.
      }
    }
  }

  Future<void> _update() async {
    // Removing every item leaves nothing to serve, so it cancels the order.
    final cancelling = _draft.isEmpty;
    if (cancelling) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Cancel order?'),
          content: const Text(
            'You removed every item. This will cancel the whole order.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Keep order'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Cancel order'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }

    setState(() => _saving = true);
    try {
      if (cancelling) {
        await ApiClient.instance.post('/orders/${widget.orderId}/cancel');
      } else {
        await ApiClient.instance.put(
          '/orders/${widget.orderId}/items',
          body: {
            'items': [
              for (final entry in _draft.entries)
                {'order_item_id': entry.key, 'quantity': entry.value},
            ],
          },
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(cancelling ? 'Order cancelled' : 'Order updated'),
        ),
      );
      _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _openCorrection(String itemId) async {
    final record = _consumption[itemId];
    final quantityController = TextEditingController(
      text: '${record?.servedQuantity ?? 0}',
    );
    final reasonController = TextEditingController();
    var submitting = false;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: const Text('Request a correction'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: quantityController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Actual quantity received',
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonController,
                decoration: const InputDecoration(labelText: 'Reason'),
                maxLines: 3,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: submitting || reasonController.text.trim().isEmpty
                  ? null
                  : () async {
                      setDialogState(() => submitting = true);
                      try {
                        final data = await ApiClient.instance.post(
                          '/orders/${widget.orderId}/items/$itemId/consumption/request-correction',
                          body: {
                            'requested_quantity':
                                int.tryParse(quantityController.text) ?? 0,
                            'reason': reasonController.text,
                          },
                        );
                        if (!mounted) return;
                        setState(() {
                          _consumption[itemId] = ConsumptionRecord.fromJson(
                            data as Map<String, dynamic>,
                          );
                        });
                        if (!dialogContext.mounted) return;
                        Navigator.of(dialogContext).pop();
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Correction requested — a server will need to validate it',
                            ),
                          ),
                        );
                      } on ApiException catch (e) {
                        setDialogState(() => submitting = false);
                        if (!dialogContext.mounted) return;
                        ScaffoldMessenger.of(
                          dialogContext,
                        ).showSnackBar(SnackBar(content: Text(e.message)));
                      }
                    },
              child: const Text('Submit for server validation'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final order = _order;
    if (_error != null) {
      return Center(
        child: Text(
          _error!,
          style: TextStyle(color: Theme.of(context).colorScheme.error),
        ),
      );
    }
    if (order == null) {
      return const Center(child: CircularProgressIndicator());
    }

    final editable = _editable.contains(order.status);
    final visibleItems = editable
        ? order.items.where((i) => _draft.containsKey(i.id))
        : order.items;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextButton.icon(
          onPressed: () => context.go('/orders'),
          icon: const Icon(Icons.arrow_back, size: 16),
          label: const Text('Back to orders'),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              order.orderNumber,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            Chip(label: Text(order.status)),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          'Type: ${order.orderType.replaceAll('_', ' ')}',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        if (order.scheduledFor != null)
          Text(
            'Scheduled for: ${DateTime.parse(order.scheduledFor!).toLocal()}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        if (order.ingredientStatus != null) ...[
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Booking status: ${order.ingredientStatus}'),
                  if (order.ingredientResponseMessage != null)
                    Text(
                      order.ingredientResponseMessage!,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: 16),
        for (final item in visibleItems)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.menuItemName ?? 'Item',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        'Qty ordered: ${editable ? _draft[item.id] : item.orderedQuantity}',
                      ),
                      if (_consumption[item.id] != null)
                        Text(
                          'Served: ${_consumption[item.id]!.servedQuantity}'
                          '${_consumption[item.id]!.status == 'CORRECTION_REQUESTED' ? ' (correction pending review)' : ''}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                    ],
                  ),
                ),
                if (editable) ...[
                  IconButton(
                    tooltip: 'Decrease quantity',
                    icon: const Icon(Icons.remove_circle_outline),
                    onPressed: _saving || _draft[item.id]! <= 1
                        ? null
                        : () => setState(
                            () => _draft[item.id] = _draft[item.id]! - 1,
                          ),
                  ),
                  IconButton(
                    tooltip: 'Remove item',
                    icon: Icon(
                      Icons.delete_outline,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    onPressed: _saving
                        ? null
                        : () => setState(() => _draft.remove(item.id)),
                  ),
                ],
                if (_consumption[item.id]?.status == 'VALIDATED')
                  OutlinedButton(
                    onPressed: () => _openCorrection(item.id),
                    child: const Text('Report an issue'),
                  ),
              ],
            ),
          ),
        if (editable) ...[
          if (_draft.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'All items removed — updating will cancel this order.',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          const SizedBox(height: 16),
          Row(
            children: [
              if (_dirty) ...[
                Expanded(
                  child: OutlinedButton(
                    onPressed: _saving ? null : () => setState(_resetDraft),
                    child: const Text('Undo changes'),
                  ),
                ),
                const SizedBox(width: 12),
              ],
              Expanded(
                child: FilledButton(
                  onPressed: _saving || !_dirty ? null : _update,
                  child: _saving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Update order'),
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
