import 'package:flutter/material.dart';

import 'employees_tab.dart';
import 'locations_tab.dart';
import 'menu_tab.dart';
import 'reports_tab.dart';

class AdministrationPage extends StatefulWidget {
  const AdministrationPage({super.key});

  @override
  State<AdministrationPage> createState() => _AdministrationPageState();
}

class _AdministrationPageState extends State<AdministrationPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController = TabController(
    length: 4,
    vsync: this,
  );

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        TabBar(
          controller: _tabController,
          isScrollable: true,
          tabs: const [
            Tab(text: 'Employees'),
            Tab(text: 'Locations'),
            Tab(text: 'Menu'),
            Tab(text: 'Reports'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [
              EmployeesTab(),
              LocationsTab(),
              MenuTab(),
              ReportsTab(),
            ],
          ),
        ),
      ],
    );
  }
}
