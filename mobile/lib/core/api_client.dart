import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'auth_storage.dart';

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

  /// Override at build/run time with
  /// `--dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1` (Android
  /// emulator's alias for the host machine) or your deployed API's URL.
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  /// Origin of the deployed React web app that serves the guest QR
  /// self-service portal (`/guest?token=...`) -- the native app hosts guests
  /// (see [ApiClient] doc comment) but points their QR at the web portal.
  /// Override with `--dart-define=WEB_APP_BASE_URL=https://mess.example.com`.
  static const String webAppBaseUrl = String.fromEnvironment(
    'WEB_APP_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

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

    switch (method) {
      case 'GET':
        return http.get(uri, headers: headers);
      case 'POST':
        return http.post(uri, headers: headers, body: encodedBody);
      case 'PUT':
        return http.put(uri, headers: headers, body: encodedBody);
      case 'PATCH':
        return http.patch(uri, headers: headers, body: encodedBody);
      default:
        throw ArgumentError('Unsupported method $method');
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
