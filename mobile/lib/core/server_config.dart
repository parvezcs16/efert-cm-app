import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Resolves which backend the app talks to.
///
/// The compile-time `API_BASE_URL` / `WEB_APP_BASE_URL` dart-defines are the
/// defaults. While [allowOverride] is on (the default for now, for testing
/// over a LAN / mobile hotspot whose IP keeps changing), a user can override
/// the server from the login screen; the override is persisted on-device.
///
/// For production builds, disable the override with
/// `--dart-define=ALLOW_SERVER_OVERRIDE=false`.
class ServerConfig {
  ServerConfig._();

  static const bool allowOverride = bool.fromEnvironment(
    'ALLOW_SERVER_OVERRIDE',
    defaultValue: true,
  );

  static const String _defaultApiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  static const String _defaultWebAppBaseUrl = String.fromEnvironment(
    'WEB_APP_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const _storage = FlutterSecureStorage();
  static const _overrideKey = 'mess_server_override';

  static String? _override;

  /// The user-entered API base URL, if any (already normalized).
  static String? get override => _override;

  static String get apiBaseUrl => _override ?? _defaultApiBaseUrl;

  /// With an override, the guest QR web portal is assumed to be served from
  /// the same origin as the API (true for the Docker/nginx setup).
  static String get webAppBaseUrl {
    final value = _override;
    if (value == null) return _defaultWebAppBaseUrl;
    return _origin(Uri.parse(value)).toString();
  }

  /// Call once at startup, before any API request.
  static Future<void> load() async {
    if (!allowOverride) return;
    try {
      _override = await _storage.read(key: _overrideKey);
    } catch (_) {
      _override = null;
    }
  }

  /// Saves [input] as the server override, or clears it when null/blank.
  /// Throws [FormatException] if the input isn't a usable address.
  static Future<void> setOverride(String? input) async {
    final trimmed = input?.trim() ?? '';
    if (trimmed.isEmpty) {
      _override = null;
      await _storage.delete(key: _overrideKey);
      return;
    }
    final normalized = normalize(trimmed);
    _override = normalized;
    await _storage.write(key: _overrideKey, value: normalized);
  }

  /// Accepts `172.23.48.119:8000`, `http://host:8080`, or a full
  /// `http://host:8000/api/v1` and returns an API base URL ending in
  /// `/api/v1` with no trailing slash.
  static String normalize(String input) {
    var value = input.trim();
    if (!value.contains('://')) value = 'http://$value';
    final uri = Uri.tryParse(value);
    if (uri == null ||
        uri.host.isEmpty ||
        (uri.scheme != 'http' && uri.scheme != 'https')) {
      throw const FormatException('Enter an address like 192.168.1.10:8000');
    }
    var path = uri.path;
    while (path.endsWith('/')) {
      path = path.substring(0, path.length - 1);
    }
    if (path.isEmpty) path = '/api/v1';
    return _origin(uri).replace(path: path).toString();
  }

  static Uri _origin(Uri uri) {
    return Uri(
      scheme: uri.scheme,
      host: uri.host,
      port: uri.hasPort ? uri.port : null,
    );
  }
}
