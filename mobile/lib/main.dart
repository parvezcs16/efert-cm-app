import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'features/auth/auth_controller.dart';

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthController()..bootstrap(),
      child: const CentralMessApp(),
    ),
  );
}
