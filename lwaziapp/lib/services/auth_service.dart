import 'dart:convert';
import 'package:http/http.dart' as http;

class AuthService {
  // Update baseUrl to match your backend host/port. For Android emulator use 10.0.2.2
  static const String baseUrl = 'http://10.0.2.2:8000';

  /// Sends username and otp to `/api/authenticate`.
  /// Returns true on success.
  static Future<bool> authenticate(String username, String otp) async {
    final uri = Uri.parse('\$baseUrl/api/authenticate');
    try {
      final resp = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'otp': otp}),
      ).timeout(const Duration(seconds: 8));

      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body);
        if (body is Map && (body['authenticated'] == true || body['token'] != null)) {
          return true;
        }
        return true; // treat 200 as success by default
      }
      return false;
    } catch (_) {
      return false;
    }
  }
}
