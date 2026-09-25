class Location {
  final String id;
  final String name;
  final String code;
  final String status;
  final String? managerId;

  Location({
    required this.id,
    required this.name,
    required this.code,
    required this.status,
    required this.managerId,
  });

  factory Location.fromJson(Map<String, dynamic> json) => Location(
    id: json['id'] as String,
    name: json['name'] as String,
    code: json['code'] as String,
    status: json['status'] as String,
    managerId: json['manager_id'] as String?,
  );
}

class KitchenStation {
  final String id;
  final String locationId;
  final String name;
  final String status;

  KitchenStation({
    required this.id,
    required this.locationId,
    required this.name,
    required this.status,
  });

  factory KitchenStation.fromJson(Map<String, dynamic> json) => KitchenStation(
    id: json['id'] as String,
    locationId: json['location_id'] as String,
    name: json['name'] as String,
    status: json['status'] as String,
  );
}
