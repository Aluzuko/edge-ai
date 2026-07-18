import 'dart:convert';
import 'package:http/http.dart' as http;

class RequestService {
  static const String baseUrl = 'http://10.0.2.2:8000';

  /// Fetches requests from `/api/requests` and returns a List of maps.
  static Future<List<Map<String, dynamic>>> fetchRequests() async {
    final uri = Uri.parse('\$baseUrl/api/requests');
    try {
      final resp = await http.get(uri).timeout(const Duration(seconds: 8));
      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body);
        if (body is List) {
          return List<Map<String, dynamic>>.from(body.map((e) => Map<String, dynamic>.from(e)));
        }
      }
      return [];
    } catch (_) {
      return [];
    }
  }
}
