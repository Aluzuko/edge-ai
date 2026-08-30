import json
import os
import threading

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

MIN_CONFIDENCE = float(os.environ.get("FCM_MIN_CONFIDENCE", "0.60"))

_lock = threading.Lock()
_credentials = None
_project_id = None
_load_error = None


def _load_credentials():
    global _credentials, _project_id, _load_error

    with _lock:
        if _credentials is not None:
            return _credentials, _project_id
        if _load_error is not None:
            return None, None

        path = os.environ.get("FCM_SERVICE_ACCOUNT_FILE")
        if not path:
            _load_error = "FCM_SERVICE_ACCOUNT_FILE is not set"
            print(f"[fcm] push disabled: {_load_error}")
            return None, None
        if not os.path.exists(path):
            _load_error = f"service account file not found: {path}"
            print(f"[fcm] push disabled: {_load_error}")
            return None, None

        try:
            from google.oauth2 import service_account
        except ImportError:
            _load_error = "google-auth is not installed (pip install google-auth)"
            print(f"[fcm] push disabled: {_load_error}")
            return None, None

        try:
            with open(path) as f:
                _project_id = json.load(f)["project_id"]
            _credentials = service_account.Credentials.from_service_account_file(
                path, scopes=[FCM_SCOPE]
            )
        except Exception as exc:
            _load_error = f"could not load service account: {exc}"
            print(f"[fcm] push disabled: {_load_error}")
            return None, None

        print(f"[fcm] push enabled for project {_project_id}")
        return _credentials, _project_id


def _access_token(credentials):
    from google.auth.transport.requests import Request

    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def build_message(token, species_name, common_name, camera_name,
                   location_description, confidence, detection_id,
                   request_id, image_id, captured_at=None):
    title = f"{common_name or species_name} detected"
    where = camera_name or "a camera"
    if location_description:
        where = f"{where} ({location_description})"
    body = f"Seen at {where} - {confidence * 100:.0f}% confidence"

    data = {
        "type": "detection",
        "detection_id": str(detection_id),
        "request_id": str(request_id),
        "image_id": str(image_id),
        "species": str(species_name),
        "camera": str(camera_name or ""),
        "confidence": f"{confidence:.4f}",
        "captured_at": str(captured_at or ""),
        "click_action": "FLUTTER_NOTIFICATION_CLICK",
    }

    return {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            "data": data,
            "android": {
                "priority": "high",
                "notification": {"channel_id": "detections"},
            },
            "apns": {
                "headers": {"apns-priority": "10"},
                "payload": {"aps": {"sound": "default"}},
            },
        }
    }


def send_message(message_body, timeout=10):
    credentials, project_id = _load_credentials()
    if credentials is None:
        return False, "fcm-not-configured"

    try:
        import requests
    except ImportError:
        return False, "requests-not-installed"

    try:
        token = _access_token(credentials)
    except Exception as exc:
        return False, f"auth-failed: {exc}"

    url = FCM_ENDPOINT.format(project_id=project_id)
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; UTF-8",
            },
            json=message_body,
            timeout=timeout,
        )
    except Exception as exc:
        return False, f"request-failed: {exc}"

    if resp.status_code == 200:
        return True, "sent"

    detail = resp.text[:300]
    if resp.status_code in (400, 403, 404):
        try:
            err = resp.json().get("error", {})
            status = err.get("status", "")
            reasons = [
                d.get("errorCode", "")
                for d in err.get("details", [])
                if isinstance(d, dict)
            ]
            if status == "NOT_FOUND" or "UNREGISTERED" in reasons:
                return False, "unregistered"
            if "INVALID_ARGUMENT" in status:
                return False, f"invalid-argument: {detail}"
        except Exception:
            pass

    return False, f"http-{resp.status_code}: {detail}"


_PENDING_TARGETS_SQL = """
SELECT
    r.request_id,
    r.ranger_id,
    dev.device_id,
    dev.fcm_token,
    dev.platform,
    s.name          AS species_name,
    s.common_name   AS common_name,
    cam.name        AS camera_name,
    cam.location_description,
    det.confidence,
    det.image_id,
    img.captured_at
FROM requests r
JOIN detections det ON det.detection_id = r.fulfilled_detection_id
JOIN species  s     ON s.species_id     = det.species_id
JOIN images   img   ON img.image_id     = det.image_id
JOIN cameras  cam   ON cam.camera_id    = img.camera_id
JOIN devices  dev   ON dev.ranger_id    = r.ranger_id
WHERE r.fulfilled_detection_id = ?
  AND r.status = 'pending'
  AND NOT EXISTS (
        SELECT 1 FROM notifications n
        WHERE n.request_id = r.request_id
          AND n.device_id  = dev.device_id
  )
"""


def notify_for_detection(db, detection_id, min_confidence=None):
    threshold = MIN_CONFIDENCE if min_confidence is None else min_confidence
    summary = {"detection_id": detection_id, "sent": 0, "failed": 0,
               "skipped": 0, "results": []}

    try:
        targets = db.execute(_PENDING_TARGETS_SQL, (detection_id,)).fetchall()
    except Exception as exc:
        summary["error"] = f"query-failed: {exc}"
        return summary

    if not targets:
        return summary

    if float(targets[0]["confidence"]) < threshold:
        summary["skipped"] = len(targets)
        summary["reason"] = (
            f"confidence {float(targets[0]['confidence']):.2f} below "
            f"threshold {threshold:.2f}"
        )
        return summary

    for t in targets:
        body = build_message(
            token=t["fcm_token"],
            species_name=t["species_name"],
            common_name=t["common_name"],
            camera_name=t["camera_name"],
            location_description=t["location_description"],
            confidence=float(t["confidence"]),
            detection_id=detection_id,
            request_id=t["request_id"],
            image_id=t["image_id"],
            captured_at=t["captured_at"],
        )
        try:
            ok, detail = send_message(body)
        except Exception as exc:
            ok, detail = False, f"send-crashed: {exc}"

        try:
            db.execute(
                """
                INSERT INTO notifications (request_id, device_id, sent_at, status)
                VALUES (?, ?, GETDATE(), ?)
                """,
                (t["request_id"], t["device_id"], "sent" if ok else "failed"),
            )
            if detail == "unregistered":
                db.execute("DELETE FROM devices WHERE device_id = ?", (t["device_id"],))
            db.commit()
        except Exception as exc:
            detail = f"{detail}; db-log-failed: {exc}"

        summary["sent" if ok else "failed"] += 1
        summary["results"].append({
            "request_id": t["request_id"],
            "device_id": t["device_id"],
            "ranger_id": t["ranger_id"],
            "ok": ok,
            "detail": detail,
        })

    return summary


def status():
    path = os.environ.get("FCM_SERVICE_ACCOUNT_FILE")
    info = {
        "env_var_set": bool(path),
        "path": path,
        "file_exists": bool(path) and os.path.exists(path),
        "google_auth_installed": True,
        "requests_installed": True,
        "min_confidence": MIN_CONFIDENCE,
    }
    try:
        import google.oauth2.service_account  # noqa: F401
    except ImportError:
        info["google_auth_installed"] = False
    try:
        import requests  # noqa: F401
    except ImportError:
        info["requests_installed"] = False

    creds, project_id = _load_credentials()
    info["configured"] = creds is not None
    info["project_id"] = project_id
    info["error"] = _load_error

    if creds is not None:
        try:
            _access_token(creds)
            info["token_ok"] = True
        except Exception as exc:
            info["token_ok"] = False
            info["error"] = f"token refresh failed: {exc}"
    return info