import logging
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.database import db_manager
from app.models.schemas import ReminderCreate, ReminderUpdate, ReminderStatus, NotificationType, NotificationChannel, NotificationCreate
from app.services.notification_service import NotificationService
from app.utils.generators import generate_id
from app.utils.calculations import to_decimal

logger = logging.getLogger("paypilot.reminders")


class ReminderService:
    @staticmethod
    def _parse_date(d_str: str) -> Optional[date]:
        try:
            return datetime.strptime(d_str.split("T")[0], "%Y-%m-%d").date()
        except Exception:
            return None

    @classmethod
    async def get_upcoming_invoices(cls, days_ahead: int = 3) -> List[Dict[str, Any]]:
        """Identify unpaid invoices approaching due date within the next N days."""
        today = date.today()
        target_cutoff = today + timedelta(days=days_ahead)
        coll = db_manager.invoices

        # Candidate invoices in pending or draft status
        candidates = await coll.find({"status": {"$in": ["pending", "draft"]}}).to_list(500)
        upcoming = []
        for inv in candidates:
            due_str = inv.get("due_date", "")
            d = cls._parse_date(due_str)
            if d and today <= d <= target_cutoff:
                inv_copy = dict(inv)
                inv_copy.pop("_id", None)
                inv_copy["days_remaining"] = (d - today).days
                upcoming.append(inv_copy)
        return upcoming

    @classmethod
    async def get_overdue_invoices(cls) -> List[Dict[str, Any]]:
        """Identify all invoices marked overdue or past due date."""
        today = date.today()
        coll = db_manager.invoices
        all_invoices = await coll.find({}).to_list(500)
        overdue = []
        for inv in all_invoices:
            due_str = inv.get("due_date", "")
            d = cls._parse_date(due_str)
            status = inv.get("status", "")
            is_overdue = (status == "overdue") or (status in ["pending", "draft"] and d and d < today)
            if is_overdue:
                inv_copy = dict(inv)
                inv_copy.pop("_id", None)
                if d:
                    inv_copy["days_overdue"] = max(0, (today - d).days)
                overdue.append(inv_copy)
        return overdue

    @classmethod
    async def check_recent_reminder(cls, invoice_id: str, window_days: int = 3) -> Optional[Dict[str, Any]]:
        """Check if a reminder was created for this invoice within the deduplication window."""
        coll = db_manager.reminders
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
        existing = await coll.find({
            "invoice_id": invoice_id,
            "created_date": {"$gte": cutoff},
            "status": {"$ne": ReminderStatus.cancelled.value},
        }).sort("created_date", -1).to_list(1)
        if existing:
            doc = dict(existing[0])
            doc.pop("_id", None)
            return doc
        return None

    @classmethod
    def generate_personalized_message(
        cls,
        invoice: Dict[str, Any],
        tone: str = "professional",
        custom_context: Optional[str] = None,
    ) -> str:
        """Generate tailored reminder copy with customer name, amount, invoice number, and due date."""
        customer_name = invoice.get("customer_name") or invoice.get("client") or "Valued Customer"
        inv_no = invoice.get("invoice_number") or invoice.get("invoice_no") or invoice.get("id")
        currency = invoice.get("currency", "INR")
        curr_symbol = "₹" if currency == "INR" else f"{currency} "
        amount = invoice.get("total_amount") or invoice.get("amount") or 0
        formatted_amount = f"{curr_symbol}{amount:,.2f}" if isinstance(amount, (int, float)) else f"{curr_symbol}{amount}"
        due_date = invoice.get("due_date", "promptly")

        status = invoice.get("status", "pending")
        days_overdue = invoice.get("days_overdue", 0)

        if status == "overdue" or days_overdue > 0:
            if tone == "urgent":
                return (
                    f"URGENT: Outstanding Invoice {inv_no} for {customer_name}. "
                    f"Your invoice of {formatted_amount} is currently {days_overdue} days overdue (Due Date: {due_date}). "
                    f"Please submit payment immediately via PayPal or contact our accounts team to prevent service disruption."
                )
            return (
                f"Dear {customer_name}, this is a gentle reminder that invoice {inv_no} for {formatted_amount} "
                f"was due on {due_date} and is currently overdue. "
                f"Please settle this balance via your PayPal payment link at your earliest convenience. Thank you!"
            )
        else:
            days_remaining = invoice.get("days_remaining", 3)
            return (
                f"Hello {customer_name}, this is an advance reminder that invoice {inv_no} for {formatted_amount} "
                f"is scheduled for payment on {due_date} (in {days_remaining} days). "
                f"You can review and pay securely using our online checkout anytime."
            )

    @classmethod
    async def create_reminder(cls, payload: ReminderCreate) -> Dict[str, Any]:
        coll = db_manager.reminders
        now = datetime.now(timezone.utc).isoformat()
        rem_id = generate_id("rem_")

        # Resolve customer name and invoice details
        customer_name = payload.customer_name
        customer_id = payload.customer_id
        customer_email = None

        invoice = await db_manager.invoices.find_one({"id": payload.invoice_id})
        if not invoice:
            invoice = await db_manager.invoices.find_one({"invoice_number": payload.invoice_id})

        if invoice:
            if not customer_name:
                customer_name = invoice.get("customer_name") or invoice.get("client")
            if not customer_id:
                customer_id = invoice.get("customer_id")
            if customer_id:
                cust = await db_manager.customers.find_one({"id": customer_id})
                if cust:
                    customer_email = cust.get("email")

        # Duplicate prevention check
        recent = await cls.check_recent_reminder(payload.invoice_id, settings.reminder_dedup_window_days)
        if recent:
            logger.info(f"Duplicate reminder prevented for invoice {payload.invoice_id}. Existing reminder: {recent['id']}")
            recent["duplicate_prevented"] = True
            return recent

        status_val = payload.status.value if hasattr(payload.status, "value") else str(payload.status)

        doc = {
            "id": rem_id,
            "invoice_id": payload.invoice_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "message": payload.message,
            "scheduled_date": payload.scheduled_date,
            "status": status_val,
            "channel": "in_app",
            "approval_status": "pending" if status_val == ReminderStatus.pending_approval.value else "approved",
            "delivery_details": None,
            "created_date": now,
        }

        await coll.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @classmethod
    async def generate_recommendations(
        cls,
        days_ahead: int = 3,
        overdue_only: bool = False,
        tone: str = "professional",
    ) -> List[Dict[str, Any]]:
        """
        Background/On-demand generator that scans invoices approaching deadline or overdue,
        prevents duplicates, and creates pending_approval reminders.
        """
        created = []
        # 1. Overdue invoices
        overdue_list = await cls.get_overdue_invoices()
        for inv in overdue_list:
            inv_id = inv.get("id") or inv.get("invoice_number")
            # Check duplicate
            if await cls.check_recent_reminder(inv_id, settings.reminder_dedup_window_days):
                continue
            msg = cls.generate_personalized_message(inv, tone=tone)
            rem = await cls.create_reminder(ReminderCreate(
                invoice_id=inv_id,
                customer_name=inv.get("customer_name") or inv.get("client"),
                customer_id=inv.get("customer_id"),
                message=msg,
                scheduled_date=datetime.now(timezone.utc).isoformat(),
                status=ReminderStatus.pending_approval,
            ))
            if not rem.get("duplicate_prevented"):
                created.append(rem)

        # 2. Upcoming invoices
        if not overdue_only:
            upcoming_list = await cls.get_upcoming_invoices(days_ahead=days_ahead)
            for inv in upcoming_list:
                inv_id = inv.get("id") or inv.get("invoice_number")
                if await cls.check_recent_reminder(inv_id, settings.reminder_dedup_window_days):
                    continue
                msg = cls.generate_personalized_message(inv, tone=tone)
                rem = await cls.create_reminder(ReminderCreate(
                    invoice_id=inv_id,
                    customer_name=inv.get("customer_name") or inv.get("client"),
                    customer_id=inv.get("customer_id"),
                    message=msg,
                    scheduled_date=inv.get("due_date", datetime.now(timezone.utc).isoformat()),
                    status=ReminderStatus.pending_approval,
                ))
                if not rem.get("duplicate_prevented"):
                    created.append(rem)

        return created

    @classmethod
    async def approve_and_send_reminder(
        cls,
        reminder_id: str,
        channel: NotificationChannel = NotificationChannel.in_app,
        custom_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Human-in-the-loop approval workflow:
        Review, optionally edit, approve, and dispatch reminder via NotificationService.
        """
        coll = db_manager.reminders
        doc = await coll.find_one({"id": reminder_id})
        if not doc:
            return {"success": False, "error": f"Reminder {reminder_id} not found"}

        message_to_send = custom_message or doc.get("message", "")
        customer_email = doc.get("customer_email")
        customer_name = doc.get("customer_name", "Customer")
        inv_id = doc.get("invoice_id", "")

        # Dispatch via notification service
        channel_val = channel.value if hasattr(channel, "value") else str(channel)
        notif_res = await NotificationService.create_notification(NotificationCreate(
            type=NotificationType.reminder,
            channel=channel,
            title=f"Payment Reminder: Invoice {inv_id}",
            message=message_to_send,
            recipient_email=customer_email if channel_val == NotificationChannel.email.value else None,
            data={"reminder_id": reminder_id, "invoice_id": inv_id, "customer_name": customer_name},
        ))

        # Check delivery outcome
        delivery_status = notif_res.get("delivery_status", "sent")
        is_failed = delivery_status == "failed"

        final_status = ReminderStatus.failed.value if is_failed else ReminderStatus.sent.value
        now = datetime.now(timezone.utc).isoformat()

        update_fields = {
            "status": final_status,
            "approval_status": "approved",
            "message": message_to_send,
            "channel": channel_val,
            "sent_date": now,
            "delivery_details": notif_res,
        }

        await coll.update_one({"id": reminder_id}, {"$set": update_fields})
        updated = await coll.find_one({"id": reminder_id})
        if updated:
            updated.pop("_id", None)
        return {
            "success": not is_failed,
            "reminder": updated,
            "notification": notif_res,
            "status": final_status,
        }

    @staticmethod
    async def get_reminders(
        invoice_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        coll = db_manager.reminders
        query = {}
        if invoice_id:
            query["invoice_id"] = invoice_id
        if status:
            query["status"] = status

        items = await coll.find(query).sort("created_date", -1).skip(offset).limit(limit).to_list(limit)
        total = await coll.count_documents(query)

        for item in items:
            item.pop("_id", None)

        return {"data": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_reminder_by_id(reminder_id: str) -> Optional[Dict[str, Any]]:
        coll = db_manager.reminders
        doc = await coll.find_one({"id": reminder_id})
        if doc:
            doc.pop("_id", None)
        return doc

    @staticmethod
    async def update_reminder(reminder_id: str, payload: ReminderUpdate) -> Optional[Dict[str, Any]]:
        coll = db_manager.reminders
        existing = await coll.find_one({"id": reminder_id})
        if not existing:
            return None

        update_data = {}
        for k, v in payload.model_dump(exclude_unset=True).items():
            if v is not None:
                update_data[k] = v.value if hasattr(v, "value") else v

        if update_data:
            await coll.update_one({"id": reminder_id}, {"$set": update_data})

        updated = await coll.find_one({"id": reminder_id})
        if updated:
            updated.pop("_id", None)
        return updated
