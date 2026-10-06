import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'app.dart';
import 'core/server_config.dart';
import 'features/auth/auth_controller.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ServerConfig.load();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthController()..bootstrap(),
      child: const CentralMessApp(),
    ),
  );
}
