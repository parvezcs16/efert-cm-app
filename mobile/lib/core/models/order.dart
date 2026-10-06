class OrderItem {
  final String id;
  final String menuItemId;
  final String? menuItemName;
  final int orderedQuantity;
  final String? kitchenStationId;

  OrderItem({
    required this.id,
    required this.menuItemId,
    required this.menuItemName,
    required this.orderedQuantity,
    required this.kitchenStationId,
  });

  factory OrderItem.fromJson(Map<String, dynamic> json) => OrderItem(
    id: json['id'] as String,
    menuItemId: json['menu_item_id'] as String,
    menuItemName: json['menu_item_name'] as String?,
    orderedQuantity: json['ordered_quantity'] as int,
    kitchenStationId: json['kitchen_station_id'] as String?,
  );
}

class Order {
  final String id;
  final String orderNumber;
  final String locationId;
  final String customerType;
  final String orderType;
  final String? scheduledFor;
  final String status;
  final String? ingredientStatus;
  final String? ingredientResponseMessage;
  final String createdAt;
  final List<OrderItem> items;

  Order({
    required this.id,
    required this.orderNumber,
    required this.locationId,
    required this.customerType,
    required this.orderType,
    required this.scheduledFor,
    required this.status,
    required this.ingredientStatus,
    required this.ingredientResponseMessage,
    required this.createdAt,
    required this.items,
  });

  factory Order.fromJson(Map<String, dynamic> json) => Order(
    id: json['id'] as String,
    orderNumber: json['order_number'] as String,
    locationId: json['location_id'] as String,
    customerType: json['customer_type'] as String,
    orderType: json['order_type'] as String,
    scheduledFor: json['scheduled_for'] as String?,
    status: json['status'] as String,
    ingredientStatus: json['ingredient_status'] as String?,
    ingredientResponseMessage: json['ingredient_response_message'] as String?,
    createdAt: json['created_at'] as String,
    items: (json['items'] as List)
        .map((e) => OrderItem.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}

const orderTypes = ['DINE_IN', 'TAKEAWAY', 'BOOK_FOR_LATER'];

class ConsumptionRecord {
  final String id;
  final String orderItemId;
  final int servedQuantity;
  final String status;
  final String servedAt;
  final int? requestedQuantity;
  final String? requestedReason;

  ConsumptionRecord({
    required this.id,
    required this.orderItemId,
    required this.servedQuantity,
    required this.status,
    required this.servedAt,
    required this.requestedQuantity,
    required this.requestedReason,
  });

  factory ConsumptionRecord.fromJson(Map<String, dynamic> json) =>
      ConsumptionRecord(
        id: json['id'] as String,
        orderItemId: json['order_item_id'] as String,
        servedQuantity: json['served_quantity'] as int,
        status: json['status'] as String,
        servedAt: json['served_at'] as String,
        requestedQuantity: json['requested_quantity'] as int?,
        requestedReason: json['requested_reason'] as String?,
      );
}
