import 'dart:async';
import 'dart:convert';
import 'dart:developer';
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;

class AuthService {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const String vapidKey = String.fromEnvironment('FCM_VAPID_KEY');

  static Future<bool> authenticate(String username, String otp) async {
    final uri = Uri.parse('$baseUrl/api/authenticate');
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
          unawaited(_registerDeviceForNotifications(username));
          return true;
        }
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  static String _platformName() {
    if (kIsWeb) return 'web';
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return 'android';
      case TargetPlatform.iOS:
        return 'ios';
      default:
        return 'web';
    }
  }

  static Future<void> _registerDeviceForNotifications(String username) async {
    final payload = <String, dynamic>{
      'username': username,
      'platform': _platformName(),
      'appName': 'lwaziapp',
    };

    try {
      final messaging = FirebaseMessaging.instance;
      final settings = await messaging
          .requestPermission(
            alert: true,
            badge: true,
            sound: true,
            provisional: false,
            carPlay: false,
            criticalAlert: false,
            announcement: false,
          )
          .timeout(const Duration(seconds: 20));

      if (settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional) {
        if (kIsWeb && vapidKey.isEmpty) {
          log(
            'FCM: web needs a VAPID key. Pass it with '
            '--dart-define=FCM_VAPID_KEY=<key from Firebase Console -> '
            'Project settings -> Cloud Messaging -> Web Push certificates>',
          );
          payload['fcm_token'] = null;
        } else {
          payload['fcm_token'] = await messaging
              .getToken(vapidKey: kIsWeb ? vapidKey : null)
              .timeout(const Duration(seconds: 20));
          log('FCM token: ${payload['fcm_token']}');
        }
      } else {
        log('FCM: permission not granted (${settings.authorizationStatus})');
      }
    } on TimeoutException {
      log(
        'FCM: timed out. On web this usually means the notification '
        'permission prompt was never answered, or '
        'web/firebase-messaging-sw.js is missing.',
      );
      payload['fcm_token'] = null;
    } catch (e, st) {
      log('FCM: getToken failed: $e', stackTrace: st);
      payload['fcm_token'] = null;
    }

    if (payload['fcm_token'] == null) {
      log('FCM: no token, skipping device registration');
      return;
    }

    try {
      final resp = await http
          .post(
            Uri.parse('$baseUrl/device-info'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 8));
      log('device-info response: ${resp.statusCode} ${resp.body}');
    } catch (e) {
      log('device-info failed: $e');
    }
  }
}
