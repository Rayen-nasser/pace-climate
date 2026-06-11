import os
import json
import asyncio
import tempfile
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from ..models import DeviceToken, ScheduledNotification, RunLog, UserGoal
from ..core.database import SessionLocal


def init_firebase():
    cred_path = os.environ.get("FCM_CREDENTIALS_PATH")
    if cred_path and os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return True
        except Exception as e:
            print(f"FCM init from file failed: {e}")

    cred_json = os.environ.get("FCM_CREDENTIALS_JSON")
    if cred_json:
        try:
            parsed = json.loads(cred_json)
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(parsed, tmp)
            tmp.flush()
            cred = credentials.Certificate(tmp.name)
            firebase_admin.initialize_app(cred)
            print(f"FCM initialized from env var (temp: {tmp.name})")
            return True
        except Exception as e:
            print(f"FCM init from env var failed: {e}")

    print("WARNING: FCM_CREDENTIALS_PATH/FCM_CREDENTIALS_JSON not configured — notifications disabled")
    return False


def build_rich_body(notif, db):
    user_id = notif.user_id
    parts = [notif.body]

    try:
        recovery = compute_recovery_local(db, user_id)
        if recovery["status"] == "rest_day":
            parts.append("🛌 Rest today — recovery is training too")
        elif recovery["status"] == "easy_day":
            parts.append("⚡ Take it easy today")
        else:
            parts.append("💪 You're ready to crush it")
    except Exception:
        pass

    try:
        goal = db.query(UserGoal).filter_by(user_id=user_id).first()
        if goal and goal.weekly_distance_km > 0:
            from .history import get_training_load
            load = get_training_load(db, user_id)
            if load and load.get("week_km"):
                pct = min(100, round(load["week_km"] / goal.weekly_distance_km * 100))
                remaining = max(0, goal.weekly_distance_km - load["week_km"])
                if pct >= 100:
                    parts.append("🎯 Weekly goal achieved! 🎉")
                elif remaining > 0:
                    parts.append(f"🎯 {remaining:.1f} km to weekly goal")
    except Exception:
        pass

    try:
        recent = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date.desc()).limit(7).all()
        if recent:
            days_with_run = 0
            for i in range(7):
                check_date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                for r in recent:
                    if r.date == check_date:
                        days_with_run += 1
                        break
            if days_with_run >= 5:
                parts.append(f"🔥 {days_with_run} runs in 7 days — on fire!")
            elif days_with_run >= 3:
                parts.append(f"💪 {days_with_run} runs this week — keep going!")
            elif days_with_run == 0:
                parts.append("🌅 Great day to start a new streak!")
    except Exception:
        pass

    return " · ".join(parts)


def compute_recovery_local(db, user_id):
    recent = db.query(RunLog).filter_by(user_id=user_id).order_by(RunLog.date.desc()).limit(5).all()
    if not recent:
        return {"status": "ready", "reason": "No recent runs — you're fresh!"}

    score = 0
    sleep = recent[0].sleep_hours or 7
    soreness = recent[0].muscle_soreness or 1
    effort = recent[0].perceived_effort or 3
    week_km = sum(r.distance_km for r in recent if r.distance_km)

    if sleep < 6:
        score += 2
    elif sleep < 7:
        score += 1
    if soreness >= 4:
        score += 2
    elif soreness >= 3:
        score += 1
    if effort >= 8:
        score += 2
    elif effort >= 6:
        score += 1
    if week_km > 50:
        score += 2
    elif week_km > 30:
        score += 1

    if score >= 4:
        return {"status": "rest_day", "reason": "High fatigue — take a rest day"}
    if score >= 2:
        return {"status": "easy_day", "reason": "Mild fatigue — keep it easy"}
    return {"status": "ready", "reason": "You're recovered and ready to run!"}


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
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            due = db.query(ScheduledNotification).filter(
                ScheduledNotification.date == today,
                ScheduledNotification.sent == 0,
            ).all()
            for notif in due:
                if notif.time and notif.time > current_time:
                    continue
                title = "🏃 PaceClimate"
                body = build_rich_body(notif, db)
                ok = send_push(notif.user_id, title, body)
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
