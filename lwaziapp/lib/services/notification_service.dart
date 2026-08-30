import 'dart:developer';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';

@pragma('vm:entry-point')
Future<void> firebaseBackgroundHandler(RemoteMessage message) async {
  log('[fcm] background message: ${message.messageId} data=${message.data}');
}

class NotificationService {
  static final GlobalKey<NavigatorState> navigatorKey =
      GlobalKey<NavigatorState>();

  static final GlobalKey<ScaffoldMessengerState> messengerKey =
      GlobalKey<ScaffoldMessengerState>();

  static Future<void> init() async {
    FirebaseMessaging.onBackgroundMessage(firebaseBackgroundHandler);

    await FirebaseMessaging.instance
        .setForegroundNotificationPresentationOptions(
      alert: true,
      badge: true,
      sound: true,
    );

    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      log('[fcm] foreground message: ${message.data}');
      _showInApp(message);
    });

    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      log('[fcm] notification tapped: ${message.data}');
      _handleTap(message);
    });

    final initial = await FirebaseMessaging.instance.getInitialMessage();
    if (initial != null) {
      log('[fcm] launched from notification: ${initial.data}');
      _handleTap(initial);
    }

    FirebaseMessaging.instance.onTokenRefresh.listen((token) {
      log('[fcm] token refreshed');
      onTokenRefresh?.call(token);
    });
  }

  static void Function(String token)? onTokenRefresh;

  static void _showInApp(RemoteMessage message) {
    final notification = message.notification;
    final title = notification?.title ?? 'Detection';
    final body = notification?.body ?? '';
    messengerKey.currentState?.showSnackBar(
      SnackBar(
        content: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
            if (body.isNotEmpty) Text(body),
          ],
        ),
        duration: const Duration(seconds: 6),
        action: SnackBarAction(
          label: 'View',
          onPressed: () => _handleTap(message),
        ),
      ),
    );
  }

  static void _handleTap(RemoteMessage message) {
    final data = message.data;
    if (data['type'] != 'detection') return;
    final detectionId = int.tryParse(data['detection_id'] ?? '');
    log('[fcm] open detection $detectionId (${data['species']} '
        'at ${data['camera']})');
  }
}
