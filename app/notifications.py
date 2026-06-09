import os
import asyncio
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from .models import DeviceToken, ScheduledNotification
from .database import SessionLocal


def init_firebase():
    cred_path = os.environ.get("FCM_CREDENTIALS_PATH")
    if not cred_path or not os.path.exists(cred_path):
        print("WARNING: FCM_CREDENTIALS_PATH not found — notifications disabled")
        return False
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        return True
    except Exception as e:
        print(f"FCM init failed: {e}")
        return False


def send_push(user_id: int, title: str, body: str):
    db = SessionLocal()
    try:
        tokens = db.query(DeviceToken.token).filter_by(user_id=user_id).all()
        if not tokens:
            return False
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=[t[0] for t in tokens],
        )
        response = messaging.send_each_for_multicast(message)
        return response.success_count > 0
    except Exception as e:
        print(f"FCM send error: {e}")
        return False
    finally:
        db.close()


async def notification_checker_loop():
    while True:
        try:
            db = SessionLocal()
            now = datetime.now(timezone.utc)
            today = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            due = db.query(ScheduledNotification).filter(
                ScheduledNotification.date == today,
                ScheduledNotification.sent == 0,
            ).all()
            for notif in due:
                if notif.time and notif.time > current_time:
                    continue
                ok = send_push(notif.user_id, notif.title, notif.body)
                if ok:
                    notif.sent = 1
                    notif.sent_at = now
            db.commit()
            db.close()
        except Exception as e:
            print(f"Notification checker error: {e}")
            try:
                db.close()
            except Exception:
                pass
        await asyncio.sleep(60)
