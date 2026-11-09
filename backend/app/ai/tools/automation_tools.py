import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.services.reminder_service import ReminderService
from app.services.financial_intelligence_service import FinancialIntelligenceService
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.models.schemas import NotificationChannel
from app.database import db_manager

logger = logging.getLogger("paypilot.ai.tools.automation")


# -------------------------------------------------------------
# 1. Get Upcoming Invoices Tool
# -------------------------------------------------------------
class GetUpcomingInvoicesInput(BaseModel):
    days_ahead: int = Field(7, ge=1, le=60, description="Number of days ahead to look for due invoices (default: 7)")


class GetUpcomingInvoicesTool(BaseTool):
    name = "get_upcoming_invoices"
    description = "Retrieves unpaid invoices approaching their due date within the specified upcoming days (e.g. this week or next 3-7 days)."
    input_schema = GetUpcomingInvoicesInput
    requires_confirmation = False

    async def run(self, days_ahead: int = 7) -> Dict[str, Any]:
        invoices = await ReminderService.get_upcoming_invoices(days_ahead=days_ahead)
        total_due = sum(float(i.get("total_amount") or i.get("amount", 0)) for i in invoices)
        return {
            "days_ahead": days_ahead,
            "upcoming_count": len(invoices),
            "total_due_amount": round(total_due, 2),
            "invoices": invoices[:10],
        }


# -------------------------------------------------------------
# 2. Get Financial Analysis Tool
# -------------------------------------------------------------
class GetFinancialAnalysisInput(BaseModel):
    include_forecast: bool = Field(True, description="Whether to include 3-month algorithmic revenue projections")


class GetFinancialAnalysisTool(BaseTool):
    name = "get_financial_analysis"
    description = (
        "Calculates comprehensive financial intelligence from database records: "
        "daily/weekly/monthly revenue, month-over-month (MoM) comparison, "
        "growth rates, revenue forecast (marked as estimate), and customer risk breakdown."
    )
    input_schema = GetFinancialAnalysisInput
    requires_confirmation = False

    async def run(self, include_forecast: bool = True) -> Dict[str, Any]:
        analysis = await FinancialIntelligenceService.get_comprehensive_analysis()
        if not include_forecast:
            analysis.pop("forecast", None)
        return analysis


# -------------------------------------------------------------
# 3. Detect Anomalies Tool
# -------------------------------------------------------------
class DetectAnomaliesInput(BaseModel):
    include_explanations: bool = Field(True, description="Include plain English AI explanations of each anomaly")


class DetectAnomaliesTool(BaseTool):
    name = "detect_anomalies"
    description = (
        "Runs transparent statistical anomaly detection across transactions, payment failures, "
        "and late-paying customers. Identifies unusually large transactions, sudden revenue drops, "
        "repeated failures, and frequent late payers."
    )
    input_schema = DetectAnomaliesInput
    requires_confirmation = False

    async def run(self, include_explanations: bool = True) -> Dict[str, Any]:
        result = await AnomalyDetectionService.detect_all_anomalies()
        return result


# -------------------------------------------------------------
# 4. Prepare Overdue Reminders Tool
# -------------------------------------------------------------
class PrepareOverdueRemindersInput(BaseModel):
    tone: str = Field("professional", description="Tone for reminders: 'professional' or 'urgent'")


class PrepareOverdueRemindersTool(BaseTool):
    name = "prepare_overdue_reminders"
    description = (
        "Scans overdue invoices, prevents duplicate reminders within the deduplication window, "
        "and stages personalized reminder drafts awaiting human review and approval."
    )
    input_schema = PrepareOverdueRemindersInput
    requires_confirmation = False

    async def run(self, tone: str = "professional") -> Dict[str, Any]:
        rems = await ReminderService.generate_recommendations(
            days_ahead=3,
            overdue_only=True,
            tone=tone,
        )
        return {
            "reminders_prepared": len(rems),
            "tone_used": tone,
            "reminders": rems,
            "status": "awaiting_user_approval",
        }


# -------------------------------------------------------------
# 5. Send Approved Reminder Tool (Mandatory Human Confirmation Gate!)
# -------------------------------------------------------------
class SendApprovedReminderInput(BaseModel):
    reminder_id: str = Field(..., description="ID of the approved reminder to dispatch")
    channel: str = Field("in_app", description="Delivery channel: 'in_app' or 'email'")


class SendApprovedReminderTool(BaseTool):
    name = "send_approved_reminder"
    description = (
        "Dispatches an approved payment reminder to a customer via in-app notification or email. "
        "SENSITIVE ACTION: Requires explicit user approval before execution."
    )
    input_schema = SendApprovedReminderInput
    requires_confirmation = True

    async def run(self, reminder_id: str, channel: str = "in_app") -> Dict[str, Any]:
        chan = NotificationChannel.email if channel == "email" else NotificationChannel.in_app
        result = await ReminderService.approve_and_send_reminder(reminder_id=reminder_id, channel=chan)
        return result


# -------------------------------------------------------------
# 6. Get Automation Logs Tool
# -------------------------------------------------------------
class GetAutomationLogsInput(BaseModel):
    limit: int = Field(10, ge=1, le=50, description="Max logs to retrieve")


class GetAutomationLogsTool(BaseTool):
    name = "get_automation_logs"
    description = "Retrieves recent execution logs and status of scheduled background tasks."
    input_schema = GetAutomationLogsInput
    requires_confirmation = False

    async def run(self, limit: int = 10) -> Dict[str, Any]:
        coll = db_manager.automation_logs
        docs = await coll.find({}).sort("executed_at", -1).limit(limit).to_list(limit)
        for d in docs:
            d.pop("_id", None)
        return {"logs": docs, "count": len(docs)}
