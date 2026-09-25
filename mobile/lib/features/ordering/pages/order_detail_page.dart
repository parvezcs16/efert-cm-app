import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api_client.dart';
import '../../../core/models/order.dart';

const _cancellable = {'PENDING', 'CONFIRMED', 'QUEUED', 'PREPARING', 'READY'};

class OrderDetailPage extends StatefulWidget {
  final String orderId;

  const OrderDetailPage({super.key, required this.orderId});

  @override
  State<OrderDetailPage> createState() => _OrderDetailPageState();
}

class _OrderDetailPageState extends State<OrderDetailPage> {
  Order? _order;
  final Map<String, ConsumptionRecord> _consumption = {};
  bool _cancelling = false;
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
      setState(() => _order = order);
      if (order.status == 'SERVED') _loadConsumption(order);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
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

  Future<void> _cancel() async {
    setState(() => _cancelling = true);
    try {
      await ApiClient.instance.post('/orders/${widget.orderId}/cancel');
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Order cancelled')));
      _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _cancelling = false);
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
        for (final item in order.items)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Qty ordered: ${item.orderedQuantity}'),
                      if (_consumption[item.id] != null)
                        Text(
                          'Served: ${_consumption[item.id]!.servedQuantity}'
                          '${_consumption[item.id]!.status == 'CORRECTION_REQUESTED' ? ' (correction pending review)' : ''}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                    ],
                  ),
                ),
                if (_consumption[item.id]?.status == 'VALIDATED')
                  OutlinedButton(
                    onPressed: () => _openCorrection(item.id),
                    child: const Text('Report an issue'),
                  ),
              ],
            ),
          ),
        if (_cancellable.contains(order.status)) ...[
          const SizedBox(height: 16),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: _cancelling ? null : _cancel,
            child: _cancelling
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Cancel order'),
          ),
        ],
      ],
    );
  }
}
