import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/models/employee.dart';
import '../features/auth/auth_controller.dart';
import 'brand.dart';

class NavDestination {
  final String path;
  final String label;
  final IconData icon;

  const NavDestination(this.path, this.label, this.icon);
}

const _baseDestinations = [
  NavDestination('/order', 'Order', Icons.restaurant_menu),
  NavDestination('/orders', 'My Orders', Icons.receipt_long),
  NavDestination('/guests', 'Guests', Icons.qr_code),
  NavDestination('/billing', 'Billing', Icons.receipt),
  NavDestination('/reviews', 'Reviews', Icons.star_rate),
];

/// Persistent scaffold (drawer nav + app bar) wrapping every authenticated
/// page -- mirrors frontend/src/components/AppLayout.tsx, but a Drawer
/// instead of a top nav bar since 7 destinations don't fit a phone-width
/// bottom bar cleanly.
class AppShell extends StatelessWidget {
  final Widget child;
  final String title;

  const AppShell({super.key, required this.child, required this.title});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthController>();
    final employee = auth.employee;

    final destinations = [
      ..._baseDestinations,
      if (employee != null && kitchenStaffRoles.contains(employee.role))
        const NavDestination('/kitchen', 'Kitchen', Icons.soup_kitchen),
      if (employee != null && adminRoles.contains(employee.role))
        const NavDestination(
          '/admin',
          'Administration',
          Icons.admin_panel_settings,
        ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        actions: const [
          Padding(padding: EdgeInsets.only(right: 12), child: _AppBarMark()),
        ],
        bottom: const PreferredSize(
          preferredSize: Size.fromHeight(4),
          child: BrandStripe(),
        ),
      ),
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              padding: EdgeInsets.zero,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          const BrandLogo(height: 48),
                          const SizedBox(height: 12),
                          if (employee != null)
                            Text('${employee.name} (${employee.pNo})'),
                        ],
                      ),
                    ),
                  ),
                  const BrandStripe(),
                ],
              ),
            ),
            for (final dest in destinations)
              ListTile(
                leading: Icon(dest.icon),
                title: Text(dest.label),
                onTap: () {
                  Navigator.pop(context);
                  context.go(dest.path);
                },
              ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout),
              title: const Text('Sign out'),
              onTap: () async {
                Navigator.pop(context);
                await auth.logout();
                if (context.mounted) context.go('/login');
              },
            ),
          ],
        ),
      ),
      body: child,
    );
  }
}

/// Logo mark on a white chip so it stays legible on the green app bar.
class _AppBarMark extends StatelessWidget {
  const _AppBarMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
      ),
      child: const BrandLogo(height: 24, showName: false),
    );
  }
}
