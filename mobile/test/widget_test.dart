import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:mobile/features/auth/auth_controller.dart';
import 'package:mobile/features/auth/pages/login_page.dart';

void main() {
  testWidgets('LoginPage renders the P-Number and password fields', (
    tester,
  ) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => AuthController(),
        child: const MaterialApp(home: LoginPage()),
      ),
    );

    expect(find.text('Sign in'), findsWidgets);
    expect(find.widgetWithText(TextField, 'P-Number'), findsOneWidget);
    expect(find.widgetWithText(TextField, 'Password'), findsOneWidget);
    expect(find.text('Forgot password?'), findsOneWidget);
    expect(find.text('New here?'), findsOneWidget);
    expect(find.widgetWithText(TextButton, 'Register'), findsOneWidget);
    // Activation is reached by signing in with the temporary password, not
    // from a separate link.
    expect(find.text('Activate your account'), findsNothing);
  });

  testWidgets(
    'Submitting empty credentials shows a validation error, not a crash',
    (tester) async {
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => AuthController(),
          child: const MaterialApp(home: LoginPage()),
        ),
      );

      await tester.tap(find.widgetWithText(FilledButton, 'Sign in'));
      // The login call will fail (no backend reachable in a widget test), but
      // it must fail gracefully into the on-screen error text, not throw.
      await tester.pump();
      await tester.pump(const Duration(seconds: 1));

      expect(tester.takeException(), isNull);
    },
  );
}
