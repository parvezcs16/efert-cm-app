import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/server_config.dart';

void main() {
  group('ServerConfig.normalize', () {
    test('adds scheme and /api/v1 to a bare ip:port', () {
      expect(
        ServerConfig.normalize('172.23.48.119:8000'),
        'http://172.23.48.119:8000/api/v1',
      );
    });

    test('keeps an explicit path and strips trailing slashes', () {
      expect(
        ServerConfig.normalize('https://mess.example.com/api/v1/'),
        'https://mess.example.com/api/v1',
      );
    });

    test('adds /api/v1 to a bare origin URL', () {
      expect(
        ServerConfig.normalize(' http://10.0.0.5:8080/ '),
        'http://10.0.0.5:8080/api/v1',
      );
    });

    test('rejects garbage', () {
      expect(() => ServerConfig.normalize('ftp://x'), throwsFormatException);
      expect(() => ServerConfig.normalize('http://'), throwsFormatException);
    });
  });
}
