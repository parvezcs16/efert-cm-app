import 'package:flutter/foundation.dart';

import '../../core/api_client.dart';
import '../../core/models/employee.dart';

enum AuthStatus { loading, authenticated, unauthenticated }

/// Mirrors frontend/src/features/auth/AuthContext.tsx.
class AuthController extends ChangeNotifier {
  final ApiClient _api = ApiClient.instance;

  Employee? employee;
  AuthStatus status = AuthStatus.loading;

  Future<void> bootstrap() async {
    final token = await _api.authStorage.getAccessToken();
    if (token == null) {
      status = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }
    await refreshProfile();
  }

  Future<void> refreshProfile() async {
    try {
      final data = await _api.get('/employees/me');
      employee = Employee.fromJson(data as Map<String, dynamic>);
      status = AuthStatus.authenticated;
    } catch (_) {
      await _api.authStorage.clear();
      employee = null;
      status = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  /// Returns true if the account still requires a mandatory password
  /// change (see docs/authentication.md's activation flow) -- callers
  /// should route to activation instead of the main app in that case.
  Future<bool> login(String pNo, String password) async {
    final data = await _api.post(
      '/auth/login',
      body: {'p_no': pNo, 'password': password},
    );
    final map = data as Map<String, dynamic>;
    await _api.authStorage.setTokens(
      map['access_token'] as String,
      map['refresh_token'] as String,
    );

    final mustChangePassword = map['must_change_password'] as bool;
    if (!mustChangePassword) {
      await refreshProfile();
    }
    return mustChangePassword;
  }

  Future<void> logout() async {
    final refreshToken = await _api.authStorage.getRefreshToken();
    if (refreshToken != null) {
      try {
        await _api.post('/auth/logout', body: {'refresh_token': refreshToken});
      } catch (_) {
        // Best-effort server-side revoke; client-side sign-out proceeds regardless.
      }
    }
    await _api.authStorage.clear();
    employee = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
