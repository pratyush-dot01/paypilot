import logging
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.database import db_manager
from app.utils.generators import generate_id
from app.models.schemas import (
    NotificationType,
    NotificationChannel,
    NotificationDeliveryStatus,
    NotificationCreate,
)

logger = logging.getLogger("paypilot.notifications")


class BaseEmailProvider:
    """Abstract interface for email delivery providers."""
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class SmtpEmailProvider(BaseEmailProvider):
    """
    Standard SMTP email provider with TLS/SSL support.
    Requires SMTP_HOST to be configured.
    """
    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.notification_email_from
        self.use_tls = settings.smtp_use_tls

    def _sync_send(self, to_email: str, subject: str, body: str, is_html: bool) -> Dict[str, Any]:
        msg = MIMEMultipart()
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html" if is_html else "plain"))

        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            if self.use_tls:
                server.starttls()
            if self.user and self.password:
                server.login(self.user, self.password)
            server.send_message(msg)
        return {"delivered": True, "provider": "smtp", "host": self.host}

    async def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> Dict[str, Any]:
        try:
            return await asyncio.to_thread(self._sync_send, to_email, subject, body, is_html)
        except Exception as e:
            logger.error(f"SMTP delivery failed to {to_email}: {e}")
            raise


class UnconfiguredEmailProvider(BaseEmailProvider):
    """
    Explicit fallback provider when SMTP credentials are not configured.
    Strictly follows rule: Never pretend an email was sent if no provider is configured.
    """
    async def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> Dict[str, Any]:
        logger.info(
            f"[NOTIFICATION NOTICE] Real email delivery skipped: SMTP provider not configured in .env. "
            f"Recipient: {to_email}, Subject: '{subject}'"
        )
        return {
            "delivered": False,
            "provider": "unconfigured",
            "reason": "SMTP credentials not configured in backend environment variables.",
            "recipient": to_email,
            "subject": subject,
        }


class NotificationService:
    """
    Multi-channel Notification System:
    - In-app notification repository
    - Configurable Email delivery with strict truthfulness
    - Delivery tracking, retry handling, and history
    """
    _email_provider: Optional[BaseEmailProvider] = None

    @classmethod
    def get_email_provider(cls) -> BaseEmailProvider:
        if cls._email_provider is None:
            if settings.smtp_host and settings.smtp_host.strip():
                cls._email_provider = SmtpEmailProvider()
            else:
                cls._email_provider = UnconfiguredEmailProvider()
        return cls._email_provider

    @classmethod
    def set_email_provider(cls, provider: BaseEmailProvider):
        """Allows injecting test mock providers during test runs."""
        cls._email_provider = provider

    @classmethod
    async def create_notification(cls, payload: NotificationCreate) -> Dict[str, Any]:
        """Create and dispatch an in-app or email notification."""
        now = datetime.now(timezone.utc).isoformat()
        notif_id = generate_id("notif_")

        channel_val = payload.channel.value if hasattr(payload.channel, "value") else str(payload.channel)
        type_val = payload.type.value if hasattr(payload.type, "value") else str(payload.type)

        delivery_status = NotificationDeliveryStatus.unread.value
        delivery_details = {}

        if channel_val == NotificationChannel.email.value:
            if not payload.recipient_email:
                delivery_status = NotificationDeliveryStatus.failed.value
                delivery_details = {"error": "Missing recipient email address"}
            else:
                provider = cls.get_email_provider()
                try:
                    result = await provider.send_email(
                        to_email=payload.recipient_email,
                        subject=payload.title,
                        body=payload.message,
                    )
                    if result.get("delivered"):
                        delivery_status = NotificationDeliveryStatus.sent.value
                        delivery_details = result
                    else:
                        # Unconfigured provider: clearly record as unconfigured
                        delivery_status = NotificationDeliveryStatus.unconfigured.value
                        delivery_details = result
                except Exception as e:
                    delivery_status = NotificationDeliveryStatus.failed.value
                    delivery_details = {"error": str(e), "attempts": 1}

        doc = {
            "id": notif_id,
            "type": type_val,
            "channel": channel_val,
            "title": payload.title,
            "message": payload.message,
            "recipient_email": payload.recipient_email,
            "data": payload.data or {},
            "read": False,
            "delivery_status": delivery_status,
            "delivery_details": delivery_details,
            "delivery_attempts": 1 if channel_val == NotificationChannel.email.value else 0,
            "created_at": now,
        }

        coll = db_manager.notifications
        await coll.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @classmethod
    async def get_notifications(
        cls,
        unread_only: bool = False,
        notif_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        coll = db_manager.notifications
        query = {}
        if unread_only:
            query["read"] = False
        if notif_type:
            query["type"] = notif_type

        docs = await coll.find(query).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
        total = await coll.count_documents(query)
        unread_count = await coll.count_documents({"read": False})

        for d in docs:
            d.pop("_id", None)

        return {
            "data": docs,
            "total": total,
            "unread_count": unread_count,
            "limit": limit,
            "offset": offset,
        }

    @classmethod
    async def mark_as_read(cls, notif_id: str) -> Optional[Dict[str, Any]]:
        coll = db_manager.notifications
        await coll.update_one({"id": notif_id}, {"$set": {"read": True}})
        doc = await coll.find_one({"id": notif_id})
        if doc:
            doc.pop("_id", None)
        return doc

    @classmethod
    async def mark_all_as_read(cls) -> int:
        coll = db_manager.notifications
        result = await coll.update_many({"read": False}, {"$set": {"read": True}})
        return getattr(result, "modified_count", 0)

    @classmethod
    async def retry_failed_notification(cls, notif_id: str, max_retries: int = 3) -> Dict[str, Any]:
        """Retry delivery for a failed notification."""
        coll = db_manager.notifications
        doc = await coll.find_one({"id": notif_id})
        if not doc:
            return {"success": False, "error": "Notification not found"}

        attempts = doc.get("delivery_attempts", 0)
        if attempts >= max_retries:
            return {"success": False, "error": f"Max retries ({max_retries}) exceeded"}

        channel = doc.get("channel")
        if channel != NotificationChannel.email.value:
            return {"success": True, "message": "In-app notifications do not require retry"}

        provider = cls.get_email_provider()
        attempts += 1
        try:
            res = await provider.send_email(
                to_email=doc["recipient_email"],
                subject=doc["title"],
                body=doc["message"],
            )
            status = NotificationDeliveryStatus.sent.value if res.get("delivered") else NotificationDeliveryStatus.unconfigured.value
            await coll.update_one(
                {"id": notif_id},
                {"$set": {
                    "delivery_status": status,
                    "delivery_attempts": attempts,
                    "delivery_details": res,
                }}
            )
            return {"success": True, "status": status, "attempts": attempts}
        except Exception as e:
            await coll.update_one(
                {"id": notif_id},
                {"$set": {
                    "delivery_status": NotificationDeliveryStatus.failed.value,
                    "delivery_attempts": attempts,
                    "delivery_details": {"error": str(e), "attempts": attempts},
                }}
            )
            return {"success": False, "error": str(e), "attempts": attempts}

