from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from ..models import User, DeviceToken, ScheduledNotification
from ..notifications import send_push

router = APIRouter(tags=["notifications"])


@router.post("/notifications/register")
async def register_device(
    token: str = Query(...),
    platform: str = Query("web"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a device token for push notifications."""
    existing = db.query(DeviceToken).filter_by(token=token).first()
    if existing:
        existing.user_id = user.id
        existing.platform = platform
    else:
        db.add(DeviceToken(user_id=user.id, token=token, platform=platform))
    db.commit()
    return {"ok": True}


@router.post("/notifications/schedule")
async def schedule_notification(
    date: str = Query(...),
    time: str = Query("17:00"),
    title: str = Query(...),
    body: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Schedule a push notification for a specific date and time."""
    n = ScheduledNotification(user_id=user.id, date=date, time=time, title=title, body=body)
    db.add(n)
    db.commit()
    return {"id": n.id, "date": date, "time": time, "title": title}


@router.get("/notifications/scheduled")
async def list_scheduled(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all unsent scheduled notifications for the current user."""
    notes = db.query(ScheduledNotification).filter_by(user_id=user.id, sent=0).order_by(ScheduledNotification.date).all()
    return {"notifications": [{"id": n.id, "date": n.date, "time": n.time, "title": n.title, "body": n.body} for n in notes]}


@router.delete("/notifications/schedule/{note_id}")
async def delete_scheduled(note_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a scheduled notification."""
    n = db.query(ScheduledNotification).filter_by(id=note_id, user_id=user.id).first()
    if n:
        db.delete(n)
        db.commit()
    return {"ok": True}


@router.post("/notifications/test")
async def test_notification(user: User = Depends(get_current_user)):
    """Send a test push notification to all registered devices."""
    ok = send_push(user.id, "🏃 Test Notification", "Reminders are working! You'll get notified at your scheduled time.")
    return {"ok": ok}
