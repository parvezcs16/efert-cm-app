import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/api_client.dart';
import '../../../core/models/location.dart';
import '../../../core/models/menu.dart';
import '../../../core/theme.dart';
import '../../../widgets/brand.dart';

class MenuTab extends StatefulWidget {
  const MenuTab({super.key});

  @override
  State<MenuTab> createState() => _MenuTabState();
}

class _MenuTabState extends State<MenuTab> {
  List<Location> _locations = [];
  String? _locationId;

  @override
  void initState() {
    super.initState();
    _loadLocations();
  }

  Future<void> _loadLocations() async {
    try {
      final data = await ApiClient.instance.get('/locations') as List;
      final locations = data
          .map((e) => Location.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() {
        _locations = locations;
        if (locations.isNotEmpty) _locationId = locations.first.id;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        DropdownButtonFormField<String>(
          initialValue: _locationId,
          decoration: const InputDecoration(labelText: 'Location'),
          items: _locations
              .map(
                (l) => DropdownMenuItem(
                  value: l.id,
                  child: Text('${l.name} (${l.code})'),
                ),
              )
              .toList(),
          onChanged: (value) => setState(() => _locationId = value),
        ),
        const SizedBox(height: 16),
        if (_locationId != null) _MenuForLocation(locationId: _locationId!),
      ],
    );
  }
}

class _MenuForLocation extends StatefulWidget {
  final String locationId;

  const _MenuForLocation({required this.locationId});

  @override
  State<_MenuForLocation> createState() => _MenuForLocationState();
}

class _MenuForLocationState extends State<_MenuForLocation> {
  List<MenuCategory>? _categories;
  final _newCategoryController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant _MenuForLocation oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.locationId != widget.locationId) _load();
  }

  @override
  void dispose() {
    _newCategoryController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _categories = null);
    try {
      final data =
          await ApiClient.instance.get(
                '/locations/${widget.locationId}/menu-categories',
              )
              as List;
      final categories = data
          .map((e) => MenuCategory.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _categories = categories);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _addCategory() async {
    try {
      await ApiClient.instance.post(
        '/locations/${widget.locationId}/menu-categories',
        body: {'name': _newCategoryController.text, 'display_order': 0},
      );
      _newCategoryController.clear();
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
    final categories = _categories;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Menu', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _newCategoryController,
                    decoration: const InputDecoration(hintText: 'New category'),
                    onChanged: (_) => setState(() {}),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _newCategoryController.text.isEmpty
                      ? null
                      : _addCategory,
                  child: const Text('Add category'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (categories == null)
              const Center(child: CircularProgressIndicator())
            else
              for (final category in categories)
                _ItemsForCategory(
                  locationId: widget.locationId,
                  category: category,
                ),
          ],
        ),
      ),
    );
  }
}

class _ItemsForCategory extends StatefulWidget {
  final String locationId;
  final MenuCategory category;

  const _ItemsForCategory({required this.locationId, required this.category});

  @override
  State<_ItemsForCategory> createState() => _ItemsForCategoryState();
}

class _ItemsForCategoryState extends State<_ItemsForCategory> {
  List<MenuItem>? _items;
  String? _busyItemId;
  final _nameController = TextEditingController();
  final _priceController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final data =
          await ApiClient.instance.get(
                '/locations/${widget.locationId}/menu-categories/${widget.category.id}/items',
              )
              as List;
      final items = data
          .map((e) => MenuItem.fromJson(e as Map<String, dynamic>))
          .toList();
      if (!mounted) return;
      setState(() => _items = items);
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _addItem() async {
    try {
      final data = await ApiClient.instance.post(
        '/locations/${widget.locationId}/menu-categories/${widget.category.id}/items',
        body: {'name': _nameController.text, 'description': null},
      );
      final item = MenuItem.fromJson(data as Map<String, dynamic>);
      if (_priceController.text.isNotEmpty) {
        await ApiClient.instance.put(
          '/locations/${widget.locationId}/menu-items/${item.id}/availability',
          body: {'is_available': true, 'price': _priceController.text},
        );
      }
      _nameController.clear();
      _priceController.clear();
      _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  String _imagePath(MenuItem item) =>
      '/locations/${widget.locationId}/menu-items/${item.id}/image';

  Future<void> _updateImage(
    MenuItem item,
    Future<dynamic> Function() action,
  ) async {
    setState(() => _busyItemId = item.id);
    try {
      final updated = MenuItem.fromJson(await action() as Map<String, dynamic>);
      if (!mounted) return;
      setState(() {
        _items = _items?.map((i) => i.id == updated.id ? updated : i).toList();
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _busyItemId = null);
    }
  }

  Future<void> _pickImage(MenuItem item) async {
    final picked = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 1200,
      maxHeight: 1200,
      imageQuality: 85,
    );
    if (picked == null) return;
    final bytes = await picked.readAsBytes();
    await _updateImage(
      item,
      () => ApiClient.instance.putFile(
        _imagePath(item),
        field: 'file',
        bytes: bytes,
        filename: picked.name,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(),
          Text(
            widget.category.name,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: BrandColors.dark,
              fontWeight: FontWeight.w600,
            ),
          ),
          if (items == null)
            const Center(child: CircularProgressIndicator())
          else
            for (final item in items)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: MenuItemImage(imageUrl: item.imageUrl, size: 48),
                title: Text(item.name),
                trailing: _busyItemId == item.id
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            tooltip: item.imageUrl == null
                                ? 'Add image'
                                : 'Replace image',
                            icon: const Icon(Icons.add_photo_alternate),
                            onPressed: () => _pickImage(item),
                          ),
                          if (item.imageUrl != null)
                            IconButton(
                              tooltip: 'Remove image',
                              icon: const Icon(Icons.delete_outline),
                              onPressed: () => _updateImage(
                                item,
                                () =>
                                    ApiClient.instance.delete(_imagePath(item)),
                              ),
                            ),
                        ],
                      ),
              ),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _nameController,
                  decoration: const InputDecoration(hintText: 'Item name'),
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: 8),
              SizedBox(
                width: 80,
                child: TextField(
                  controller: _priceController,
                  decoration: const InputDecoration(hintText: 'Price'),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: _nameController.text.isEmpty ? null : _addItem,
                child: const Text('Add'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
