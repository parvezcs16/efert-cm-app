class MenuCategory {
  final String id;
  final String locationId;
  final String name;
  final int displayOrder;
  final String status;

  MenuCategory({
    required this.id,
    required this.locationId,
    required this.name,
    required this.displayOrder,
    required this.status,
  });

  factory MenuCategory.fromJson(Map<String, dynamic> json) => MenuCategory(
    id: json['id'] as String,
    locationId: json['location_id'] as String,
    name: json['name'] as String,
    displayOrder: json['display_order'] as int,
    status: json['status'] as String,
  );
}

class MenuItem {
  final String id;
  final String categoryId;
  final String name;
  final String? description;
  final String? imageUrl;
  final String status;

  MenuItem({
    required this.id,
    required this.categoryId,
    required this.name,
    required this.description,
    required this.imageUrl,
    required this.status,
  });

  factory MenuItem.fromJson(Map<String, dynamic> json) => MenuItem(
    id: json['id'] as String,
    categoryId: json['category_id'] as String,
    name: json['name'] as String,
    description: json['description'] as String?,
    imageUrl: json['image_url'] as String?,
    status: json['status'] as String,
  );
}

/// Price-free -- matches app/schemas/menu.py:MenuBrowseItem. Employees
/// (and guests) never see prices in the ordering UX (CLAUDE.md).
class MenuBrowseItem {
  final String id;
  final String name;
  final String? description;
  final String? imageUrl;

  MenuBrowseItem({
    required this.id,
    required this.name,
    required this.description,
    required this.imageUrl,
  });

  factory MenuBrowseItem.fromJson(Map<String, dynamic> json) => MenuBrowseItem(
    id: json['id'] as String,
    name: json['name'] as String,
    description: json['description'] as String?,
    imageUrl: json['image_url'] as String?,
  );
}

class MenuBrowseCategory {
  final String id;
  final String name;
  final int displayOrder;
  final List<MenuBrowseItem> items;

  MenuBrowseCategory({
    required this.id,
    required this.name,
    required this.displayOrder,
    required this.items,
  });

  factory MenuBrowseCategory.fromJson(Map<String, dynamic> json) =>
      MenuBrowseCategory(
        id: json['id'] as String,
        name: json['name'] as String,
        displayOrder: json['display_order'] as int,
        items: (json['items'] as List)
            .map((e) => MenuBrowseItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class MenuItemLocation {
  final String id;
  final String menuItemId;
  final String locationId;
  final bool isAvailable;
  final String price;
  final String? effectiveFrom;
  final String? effectiveTo;

  MenuItemLocation({
    required this.id,
    required this.menuItemId,
    required this.locationId,
    required this.isAvailable,
    required this.price,
    required this.effectiveFrom,
    required this.effectiveTo,
  });

  factory MenuItemLocation.fromJson(Map<String, dynamic> json) =>
      MenuItemLocation(
        id: json['id'] as String,
        menuItemId: json['menu_item_id'] as String,
        locationId: json['location_id'] as String,
        isAvailable: json['is_available'] as bool,
        price: json['price'] as String,
        effectiveFrom: json['effective_from'] as String?,
        effectiveTo: json['effective_to'] as String?,
      );
}
