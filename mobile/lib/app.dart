import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'features/administration/pages/administration_page.dart';
import 'features/auth/auth_controller.dart';
import 'features/auth/pages/activation_page.dart';
import 'features/auth/pages/forgot_password_page.dart';
import 'features/auth/pages/login_page.dart';
import 'features/auth/pages/register_page.dart';
import 'features/billing/pages/billing_page.dart';
import 'features/guests/pages/guests_page.dart';
import 'features/kitchen/pages/kitchen_page.dart';
import 'features/ordering/pages/order_detail_page.dart';
import 'features/ordering/pages/ordering_page.dart';
import 'features/ordering/pages/orders_page.dart';
import 'features/reviews/pages/reviews_page.dart';
import 'widgets/app_shell.dart';

const _publicPaths = {'/login', '/register', '/activate', '/forgot-password'};

/// SERVER/KITCHEN_OPERATOR's day-to-day job is the kitchen screen, not
/// placing their own order -- mirrors frontend/src/components/RoleHome.tsx.
/// "/order" (distinct from "/") stays reachable so they can still place a
/// personal order without the redirect bouncing them straight back.
const _kitchenOnlyRoles = ['SERVER', 'KITCHEN_OPERATOR'];

GoRouter buildRouter(AuthController auth) {
  return GoRouter(
    refreshListenable: auth,
    initialLocation: '/',
    redirect: (context, state) {
      final loggedIn = auth.status == AuthStatus.authenticated;
      final loggingIn = _publicPaths.contains(state.matchedLocation);

      if (auth.status == AuthStatus.loading) return null;
      if (!loggedIn && !loggingIn) return '/login';
      if (loggedIn && loggingIn) return '/';
      if (loggedIn &&
          state.matchedLocation == '/' &&
          _kitchenOnlyRoles.contains(auth.employee?.role)) {
        return '/kitchen';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginPage()),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterPage(),
      ),
      GoRoute(
        path: '/activate',
        builder: (context, state) =>
            ActivationPage(initialPNo: state.extra as String?),
      ),
      GoRoute(
        path: '/forgot-password',
        builder: (context, state) => const ForgotPasswordPage(),
      ),
      ShellRoute(
        builder: (context, state, child) =>
            AppShell(title: _titleFor(state.matchedLocation), child: child),
        routes: [
          GoRoute(path: '/', builder: (context, state) => const OrderingPage()),
          GoRoute(
            path: '/order',
            builder: (context, state) => const OrderingPage(),
          ),
          GoRoute(
            path: '/orders',
            builder: (context, state) => const OrdersPage(),
          ),
          GoRoute(
            path: '/orders/:orderId',
            builder: (context, state) =>
                OrderDetailPage(orderId: state.pathParameters['orderId']!),
          ),
          GoRoute(
            path: '/guests',
            builder: (context, state) => const GuestsPage(),
          ),
          GoRoute(
            path: '/kitchen',
            builder: (context, state) => const KitchenPage(),
          ),
          GoRoute(
            path: '/billing',
            builder: (context, state) => const BillingPage(),
          ),
          GoRoute(
            path: '/reviews',
            builder: (context, state) => const ReviewsPage(),
          ),
          GoRoute(
            path: '/admin',
            builder: (context, state) => const AdministrationPage(),
          ),
        ],
      ),
    ],
  );
}

String _titleFor(String path) {
  return switch (path) {
    '/' || '/order' => 'Order',
    '/orders' => 'My Orders',
    '/guests' => 'Guests',
    '/kitchen' => 'Kitchen',
    '/billing' => 'Billing',
    '/reviews' => 'Reviews',
    '/admin' => 'Administration',
    _ => 'Central Mess',
  };
}

class CentralMessApp extends StatefulWidget {
  const CentralMessApp({super.key});

  @override
  State<CentralMessApp> createState() => _CentralMessAppState();
}

class _CentralMessAppState extends State<CentralMessApp> {
  // Built once: GoRouter's own `refreshListenable` re-runs `redirect` when
  // AuthController notifies, so recreating the router itself on every auth
  // change (which would also blow away navigation history) isn't needed.
  late final GoRouter _router = buildRouter(context.read<AuthController>());

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Central Mess',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      routerConfig: _router,
    );
  }
}
