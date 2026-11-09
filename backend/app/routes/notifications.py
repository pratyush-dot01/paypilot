from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from app.services.notification_service import NotificationService
from app.models.schemas import NotificationCreate

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/")
async def list_notifications(
    unread_only: bool = Query(False),
    type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieve notifications with unread counts and delivery states."""
    return await NotificationService.get_notifications(
        unread_only=unread_only,
        notif_type=type,
        limit=limit,
        offset=offset,
    )


@router.post("/", status_code=201)
async def create_notification(payload: NotificationCreate):
    """Create and dispatch a notification (in-app or email)."""
    return await NotificationService.create_notification(payload)


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark an individual notification as read."""
    doc = await NotificationService.mark_as_read(notification_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Notification not found")
    return doc


@router.post("/mark-all-read")
async def mark_all_read():
    """Mark all unread notifications as read."""
    count = await NotificationService.mark_all_as_read()
    return {"status": "success", "marked_read_count": count}


@router.post("/retry/{notification_id}")
async def retry_notification(notification_id: str):
    """Retry delivery for a failed notification."""
    res = await NotificationService.retry_failed_notification(notification_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Retry failed"))
    return res

