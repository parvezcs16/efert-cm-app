import 'api_client.dart';

/// Mirrors frontend/src/lib/ws.ts, deriving the socket origin from
/// [ApiClient.baseUrl] (which already points at `<host>/api/v1`) instead of
/// `window.location` since there is no browser origin on native.
String kitchenSocketUrl(String locationId, String token) {
  final apiUri = Uri.parse(ApiClient.baseUrl);
  final scheme = apiUri.scheme == 'https' ? 'wss' : 'ws';
  final socketUri = Uri(
    scheme: scheme,
    host: apiUri.host,
    port: apiUri.hasPort ? apiUri.port : null,
    path: '/ws/kitchen/$locationId',
    queryParameters: {'token': token},
  );
  return socketUri.toString();
}
