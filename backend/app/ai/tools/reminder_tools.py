"""
Reminder Tools for PayPilot AI Agent (Phase 5).
Interacts directly with ReminderService to generate and schedule payment reminders.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.ai.tools.base import BaseTool
from app.services.reminder_service import ReminderService
from app.services.invoice_service import InvoiceService
from app.models.schemas import ReminderCreate, ReminderStatus

class GeneratePaymentReminderInput(BaseModel):
    invoice_id: str = Field(..., description="Invoice ID or invoice number to generate a reminder message for")
    custom_note: Optional[str] = Field(None, description="Optional custom context or urgency note to include in the reminder")

class GeneratePaymentReminderTool(BaseTool):
    name = "generate_payment_reminder"
    description = "Draft a professional payment reminder message for an overdue or pending invoice."
    input_schema = GeneratePaymentReminderInput

    async def run(self, invoice_id: str, custom_note: Optional[str] = None) -> Dict[str, Any]:
        inv = await InvoiceService.get_invoice_by_id(invoice_id)
        if not inv:
            return {"success": False, "error": f"Invoice '{invoice_id}' not found"}

        client = inv.get("customer_name", "Valued Client")
        inv_no = inv.get("invoice_number", invoice_id)
        amount = inv.get("total_amount", 0.0)
        curr = inv.get("currency", "INR")
        due = inv.get("due_date", "as soon as possible")

        note_part = f" Note: {custom_note}" if custom_note else ""
        message = (
            f"Dear {client}, this is a friendly reminder that invoice {inv_no} "
            f"for {curr} {amount:,.2f} was due on {due}. Please complete the payment "
            f"at your earliest convenience.{note_part}"
        )

        return {
            "success": True,
            "invoice_id": inv["id"],
            "invoice_number": inv_no,
            "customer_name": client,
            "amount": amount,
            "currency": curr,
            "due_date": due,
            "draft_message": message,
        }

class CreateReminderInput(BaseModel):
    invoice_id: str = Field(..., description="Invoice ID or invoice number")
    message: str = Field(..., min_length=5, description="The reminder message to schedule")
    scheduled_date: Optional[str] = Field(None, description="Scheduled date in YYYY-MM-DD format (defaults to tomorrow)")

class CreateReminderTool(BaseTool):
    name = "create_reminder"
    description = "Schedule and persist an official payment reminder record in the database."
    input_schema = CreateReminderInput

    async def run(
        self,
        invoice_id: str,
        message: str,
        scheduled_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        inv = await InvoiceService.get_invoice_by_id(invoice_id)
        if not inv:
            return {"success": False, "error": f"Invoice '{invoice_id}' not found"}

        if not scheduled_date:
            scheduled_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        payload = ReminderCreate(
            invoice_id=inv["id"],
            customer_name=inv.get("customer_name"),
            customer_id=inv.get("customer_id"),
            message=message,
            scheduled_date=scheduled_date,
            status=ReminderStatus.scheduled,
        )
        created = await ReminderService.create_reminder(payload)
        return {
            "success": True,
            "reminder_id": created["id"],
            "invoice_id": created["invoice_id"],
            "customer_name": created.get("customer_name"),
            "message": created["message"],
            "scheduled_date": created["scheduled_date"],
            "status": created["status"],
        }

