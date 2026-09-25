class SalesSummary {
  final int totalOrders;
  final Map<String, int> ordersByStatus;
  final Map<String, int> ordersByType;
  final String totalRevenue;

  SalesSummary({
    required this.totalOrders,
    required this.ordersByStatus,
    required this.ordersByType,
    required this.totalRevenue,
  });

  factory SalesSummary.fromJson(Map<String, dynamic> json) => SalesSummary(
    totalOrders: json['total_orders'] as int,
    ordersByStatus: Map<String, int>.from(json['orders_by_status'] as Map),
    ordersByType: Map<String, int>.from(json['orders_by_type'] as Map),
    totalRevenue: json['total_revenue'] as String,
  );
}

class ReconciliationLine {
  final String orderId;
  final String orderNumber;
  final String orderItemId;
  final int orderedQuantity;
  final int servedQuantity;
  final String expectedAmount;
  final String billedAmount;
  final bool matches;

  ReconciliationLine({
    required this.orderId,
    required this.orderNumber,
    required this.orderItemId,
    required this.orderedQuantity,
    required this.servedQuantity,
    required this.expectedAmount,
    required this.billedAmount,
    required this.matches,
  });

  factory ReconciliationLine.fromJson(Map<String, dynamic> json) =>
      ReconciliationLine(
        orderId: json['order_id'] as String,
        orderNumber: json['order_number'] as String,
        orderItemId: json['order_item_id'] as String,
        orderedQuantity: json['ordered_quantity'] as int,
        servedQuantity: json['served_quantity'] as int,
        expectedAmount: json['expected_amount'] as String,
        billedAmount: json['billed_amount'] as String,
        matches: json['matches'] as bool,
      );
}

class ReconciliationReport {
  final List<ReconciliationLine> lines;
  final int mismatchCount;

  ReconciliationReport({required this.lines, required this.mismatchCount});

  factory ReconciliationReport.fromJson(Map<String, dynamic> json) =>
      ReconciliationReport(
        lines: (json['lines'] as List)
            .map((e) => ReconciliationLine.fromJson(e as Map<String, dynamic>))
            .toList(),
        mismatchCount: json['mismatch_count'] as int,
      );
}

class AuditLogEntry {
  final String id;
  final String? actorEmployeeId;
  final String action;
  final String entityType;
  final String? entityId;
  final String createdAt;

  AuditLogEntry({
    required this.id,
    required this.actorEmployeeId,
    required this.action,
    required this.entityType,
    required this.entityId,
    required this.createdAt,
  });

  factory AuditLogEntry.fromJson(Map<String, dynamic> json) => AuditLogEntry(
    id: json['id'] as String,
    actorEmployeeId: json['actor_employee_id'] as String?,
    action: json['action'] as String,
    entityType: json['entity_type'] as String,
    entityId: json['entity_id'] as String?,
    createdAt: json['created_at'] as String,
  );
}
