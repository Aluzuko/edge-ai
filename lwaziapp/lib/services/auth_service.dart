import 'dart:convert';
import 'dart:developer';
import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;

class AuthService {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static Future<bool> authenticate(String username, String otp) async {
    final uri = Uri.parse('$baseUrl/authenticate');
    try {
      print('AuthService.authenticate request: $username, $otp, $uri');
      final resp = await http
          .post(
            uri,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'username': username, 'otp': otp}),
          )
          .timeout(const Duration(seconds: 8));

      print(
        'AuthService.authenticate response: ${resp.statusCode} ${resp.body}',
      );
      print(resp);
      log('AuthService.authenticate response: ${resp.statusCode} ${resp.body}');
      if (resp.statusCode == 200) {
        final body = jsonDecode(resp.body);
        final authenticated = body is Map && body['authenticated'] == true;
        if (authenticated) {
          await _registerDeviceForNotifications(username);
          return true;
        }
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  static Future<void> _registerDeviceForNotifications(String username) async {
    final payload = <String, dynamic>{
      'username': username,
      'platform': Platform.operatingSystem,
      'platformVersion': Platform.operatingSystemVersion,
      'appName': 'lwaziapp',
    };

    try {
      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
        carPlay: false,
        criticalAlert: false,
        announcement: false,
      );

      if (settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional) {
        payload['fcmToken'] = await messaging.getToken();
      }
    } catch (_) {
      payload['fcmToken'] = null;
    }

    try {
      await http
          .post(
            Uri.parse('$baseUrl/device-info'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 8));
    } catch (_) {
      // Ignore registration failures so the user can still continue to the app.
    }
  }
}
