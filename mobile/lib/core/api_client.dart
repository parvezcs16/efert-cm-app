import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'auth_storage.dart';
import 'server_config.dart';

class ApiException implements Exception {
  final String message;
  final int status;
  final String? errorCode;

  ApiException(this.message, this.status, [this.errorCode]);

  @override
  String toString() => message;
}

/// Mirrors frontend/src/lib/api.ts: attaches the employee bearer token to
/// every request and transparently refreshes+retries once on a 401. Guest
/// self-service intentionally has no client here -- see
/// docs/implementation-notes.md "Mobile app": guests use the existing web
/// QR flow, not this native app.
class ApiClient {
  ApiClient._();

  static final ApiClient instance = ApiClient._();

  /// Set at build/run time with
  /// `--dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1` (Android
  /// emulator's alias for the host machine) or your deployed API's URL, or
  /// overridden on-device from the login screen -- see [ServerConfig].
  static String get baseUrl => ServerConfig.apiBaseUrl;

  /// Origin of the deployed React web app that serves the guest QR
  /// self-service portal (`/guest?token=...`) -- the native app hosts guests
  /// (see [ApiClient] doc comment) but points their QR at the web portal.
  /// Set with `--dart-define=WEB_APP_BASE_URL=https://mess.example.com`.
  static String get webAppBaseUrl => ServerConfig.webAppBaseUrl;

  static const Duration _timeout = Duration(seconds: 15);

  /// Resolves a server-relative media path (e.g. `/media/menu/x.jpg`, as
  /// returned in `image_url`) against the API's origin.
  static String? mediaUrl(String? path) {
    if (path == null || path.isEmpty) return null;
    return Uri.parse(baseUrl).resolve(path).toString();
  }

  final EmployeeAuthStorage authStorage = EmployeeAuthStorage();
  Future<bool>? _refreshInFlight;

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _request('GET', path, query: query);

  Future<dynamic> post(String path, {Map<String, dynamic>? body}) =>
      _request('POST', path, body: body);

  Future<dynamic> put(String path, {Map<String, dynamic>? body}) =>
      _request('PUT', path, body: body);

  Future<dynamic> patch(String path, {Map<String, dynamic>? body}) =>
      _request('PATCH', path, body: body);

  Future<dynamic> delete(String path) => _request('DELETE', path);

  /// Multipart PUT of a single file field (used for menu item images).
  /// Same auth + refresh-once-on-401 behavior as the JSON helpers.
  Future<dynamic> putFile(
    String path, {
    required String field,
    required List<int> bytes,
    required String filename,
  }) async {
    final uri = _buildUri(path, null);

    Future<http.Response> send(String? token) async {
      final request = http.MultipartRequest('PUT', uri)
        ..files.add(
          http.MultipartFile.fromBytes(field, bytes, filename: filename),
        );
      if (token != null) request.headers['Authorization'] = 'Bearer $token';
      return http.Response.fromStream(await request.send());
    }

    final token = await authStorage.getAccessToken();
    var response = await send(token);
    if (response.statusCode == 401 && token != null) {
      if (await _refreshToken()) {
        response = await send(await authStorage.getAccessToken());
      } else {
        await authStorage.clear();
      }
    }
    return _parse(response);
  }

  Uri _buildUri(String path, Map<String, dynamic>? query) {
    final uri = Uri.parse('$baseUrl$path');
    if (query == null || query.isEmpty) return uri;

    // Supports repeated keys (e.g. ?role=A&role=B for the employee
    // directory filter), which a plain Map<String,String> can't express.
    final params = <String, List<String>>{};
    query.forEach((key, value) {
      if (value == null) return;
      params[key] = value is List
          ? value.map((e) => e.toString()).toList()
          : [value.toString()];
    });
    return uri.replace(queryParameters: params);
  }

  Future<http.Response> _send(
    String method,
    Uri uri,
    String? token,
    Map<String, dynamic>? body,
  ) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
    final encodedBody = body != null ? jsonEncode(body) : null;

    final Future<http.Response> response;
    switch (method) {
      case 'GET':
        response = http.get(uri, headers: headers);
      case 'POST':
        response = http.post(uri, headers: headers, body: encodedBody);
      case 'PUT':
        response = http.put(uri, headers: headers, body: encodedBody);
      case 'PATCH':
        response = http.patch(uri, headers: headers, body: encodedBody);
      case 'DELETE':
        response = http.delete(uri, headers: headers);
      default:
        throw ArgumentError('Unsupported method $method');
    }
    return _guardNetwork(response);
  }

  /// Turns "server unreachable" failures (wrong IP, firewall, different
  /// network) into an [ApiException] naming the server, instead of a
  /// generic error or a multi-minute hang.
  Future<http.Response> _guardNetwork(Future<http.Response> response) async {
    try {
      return await response.timeout(_timeout);
    } on TimeoutException {
      throw ApiException(
        'Server at ${Uri.parse(baseUrl).authority} is not responding',
        0,
      );
    } on http.ClientException {
      throw ApiException(
        'Cannot reach server at ${Uri.parse(baseUrl).authority}',
        0,
      );
    }
  }

  Future<dynamic> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    Map<String, dynamic>? query,
  }) async {
    final uri = _buildUri(path, query);
    final token = await authStorage.getAccessToken();

    var response = await _send(method, uri, token, body);

    if (response.statusCode == 401 && token != null) {
      final refreshed = await _refreshToken();
      if (refreshed) {
        final newToken = await authStorage.getAccessToken();
        response = await _send(method, uri, newToken, body);
      } else {
        await authStorage.clear();
      }
    }

    return _parse(response);
  }

  /// Shared in-flight refresh so concurrent 401s don't each fire their own
  /// refresh call and race each other.
  Future<bool> _refreshToken() {
    return _refreshInFlight ??= _doRefresh().whenComplete(() {
      _refreshInFlight = null;
    });
  }

  Future<bool> _doRefresh() async {
    final refreshToken = await authStorage.getRefreshToken();
    if (refreshToken == null) return false;

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/token/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': refreshToken}),
      );
      if (response.statusCode != 200) return false;
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await authStorage.setTokens(
        data['access_token'] as String,
        data['refresh_token'] as String,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  dynamic _parse(http.Response response) {
    if (response.statusCode == 204 || response.body.isEmpty) {
      if (response.statusCode >= 400) {
        throw ApiException('Request failed', response.statusCode);
      }
      return null;
    }

    final decoded = jsonDecode(response.body);
    if (response.statusCode >= 400) {
      final map = decoded is Map<String, dynamic>
          ? decoded
          : <String, dynamic>{};
      throw ApiException(
        (map['message'] as String?) ?? 'Something went wrong',
        response.statusCode,
        map['error_code'] as String?,
      );
    }
    return decoded;
  }
}
