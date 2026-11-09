from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from app.models.schemas import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderStatus,
    ReminderApprovalRequest,
    BatchReminderGenerateRequest,
    NotificationChannel,
)
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/api/reminders", tags=["Reminder Management"])


@router.post("/generate-recommendations")
async def generate_reminder_recommendations(payload: BatchReminderGenerateRequest):
    """
    Scan pending/overdue invoices, prevent duplicates, and generate
    personalized reminder recommendations awaiting human review.
    """
    rems = await ReminderService.generate_recommendations(
        days_ahead=payload.days_ahead,
        overdue_only=payload.overdue_only,
        tone=payload.tone,
    )
    return {"generated_count": len(rems), "reminders": rems}


@router.post("/{reminder_id}/approve")
async def approve_and_send_reminder(reminder_id: str, payload: Optional[ReminderApprovalRequest] = None):
    """
    Human-in-the-loop review and approval workflow:
    Approves the reminder and dispatches it via NotificationService (in-app or email).
    """
    channel = payload.channel if payload else NotificationChannel.in_app
    custom_msg = payload.custom_message if payload else None

    res = await ReminderService.approve_and_send_reminder(
        reminder_id=reminder_id,
        channel=channel,
        custom_message=custom_msg,
    )
    if not res.get("success", False) and "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.get("/upcoming-invoices")
async def get_upcoming_invoices(days_ahead: int = Query(3, ge=1, le=30)):
    """Retrieve unpaid invoices approaching their due date."""
    invoices = await ReminderService.get_upcoming_invoices(days_ahead=days_ahead)
    return {"data": invoices, "total": len(invoices), "days_ahead": days_ahead}


@router.get("/overdue-invoices")
async def get_overdue_invoices():
    """Retrieve all invoices that are overdue."""
    invoices = await ReminderService.get_overdue_invoices()
    return {"data": invoices, "total": len(invoices)}


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(payload: ReminderCreate):
    """Create a new payment reminder record."""
    return await ReminderService.create_reminder(payload)

@router.get("/")
async def get_reminders(
    invoice_id: Optional[str] = Query(None, description="Filter by associated invoice ID"),
    status: Optional[str] = Query(None, description="Filter by status: scheduled, sent, cancelled"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieve reminders with optional filters."""
    return await ReminderService.get_reminders(
        invoice_id=invoice_id,
        status=status,
        limit=limit,
        offset=offset,
    )

@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(reminder_id: str):
    """Retrieve a specific reminder by ID."""
    rem = await ReminderService.get_reminder_by_id(reminder_id)
    if not rem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with ID '{reminder_id}' not found",
        )
    return rem

@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(reminder_id: str, payload: ReminderUpdate):
    """Update a reminder's message, date, or status."""
    updated = await ReminderService.update_reminder(reminder_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with ID '{reminder_id}' not found",
        )
    return updated

@router.patch("/{reminder_id}/status", response_model=ReminderResponse)
async def update_reminder_status(reminder_id: str, status: ReminderStatus):
    """Update the status of a reminder (e.g., mark as sent or cancelled)."""
    updated = await ReminderService.update_reminder(reminder_id, ReminderUpdate(status=status))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with ID '{reminder_id}' not found",
        )
    return updated

