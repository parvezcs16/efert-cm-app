import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Mirrors frontend/src/lib/auth-storage.ts. Uses the platform keystore
/// (Android Keystore / iOS Keychain via flutter_secure_storage) rather than
/// plain SharedPreferences, since these are long-lived bearer credentials.
class EmployeeAuthStorage {
  static const _storage = FlutterSecureStorage();
  static const _accessKey = 'mess_access_token';
  static const _refreshKey = 'mess_refresh_token';

  Future<String?> getAccessToken() => _storage.read(key: _accessKey);
  Future<String?> getRefreshToken() => _storage.read(key: _refreshKey);

  Future<void> setTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: _accessKey, value: accessToken);
    await _storage.write(key: _refreshKey, value: refreshToken);
  }

  Future<void> setAccessToken(String accessToken) =>
      _storage.write(key: _accessKey, value: accessToken);

  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}
