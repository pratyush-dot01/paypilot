import logging
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.database import db_manager
from app.services.invoice_service import InvoiceService
from app.services.reminder_service import ReminderService
from app.services.financial_intelligence_service import FinancialIntelligenceService
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.notification_service import NotificationService
from app.models.schemas import NotificationType, NotificationChannel, NotificationCreate
from app.utils.generators import generate_id

logger = logging.getLogger("paypilot.scheduler")


class SchedulerService:
    """
    Enterprise Background Automation Scheduler using APScheduler:
    - Singleton instance preventing duplicate schedulers on Uvicorn reload.
    - Automated logging to `automation_logs` collection.
    - Safe error containment per job.
    - Direct programmatic execution for immediate runs and test suites.
    """
    _instance: Optional["SchedulerService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self._job_definitions = {}
        self._initialized = True

    async def _log_execution(
        self,
        job_id: str,
        job_name: str,
        status: str,
        summary: str,
        duration_ms: float,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Record structured job run to automation_logs collection."""
        log_entry = {
            "id": generate_id("log_"),
            "job_id": job_id,
            "job_name": job_name,
            "status": status,
            "summary": summary,
            "details": details or {},
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": round(duration_ms, 2),
        }
        try:
            coll = db_manager.automation_logs
            await coll.insert_one(log_entry)
        except Exception as e:
            logger.warning(f"Could not persist automation log: {e}")

    # ---------------------------------------------------------
    # Scheduled Job Implementations
    # ---------------------------------------------------------

    async def job_check_overdue_invoices(self) -> Dict[str, Any]:
        """Job 1: Scan all invoices and mark overdue ones, notifying admin."""
        start = time.time()
        job_name = "Check Overdue Invoices"
        try:
            logger.info("Executing scheduled task: Check Overdue Invoices...")
            overdue_list = await ReminderService.get_overdue_invoices()
            for inv in overdue_list:
                # Update status in db if still pending
                if inv.get("status") != "overdue":
                    await db_manager.invoices.update_one(
                        {"id": inv["id"]},
                        {"$set": {"status": "overdue", "updated_date": datetime.now(timezone.utc).isoformat()}}
                    )

            count = len(overdue_list)
            summary = f"Detected and updated {count} overdue invoice(s)."

            if count > 0:
                # Create in-app notification
                await NotificationService.create_notification(NotificationCreate(
                    type=NotificationType.overdue_alert,
                    channel=NotificationChannel.in_app,
                    title=f"Overdue Invoices Alert: {count} Account(s)",
                    message=f"{count} invoice(s) are currently past their due date. Review and generate reminder notices.",
                    data={"overdue_count": count},
                ))

            dur = (time.time() - start) * 1000
            await self._log_execution("check_overdue_invoices", job_name, "success", summary, dur, {"count": count})
            return {"success": True, "count": count, "summary": summary}
        except Exception as e:
            dur = (time.time() - start) * 1000
            err_summary = f"Failure checking overdue invoices: {str(e)}"
            logger.error(err_summary)
            await self._log_execution("check_overdue_invoices", job_name, "failed", err_summary, dur, {"error": str(e)})
            return {"success": False, "error": str(e)}

    async def job_identify_upcoming_due_invoices(self) -> Dict[str, Any]:
        """Job 2: Identify invoices approaching due date in next 3 days."""
        start = time.time()
        job_name = "Identify Invoices Approaching Due Date"
        try:
            logger.info("Executing scheduled task: Upcoming Due Invoices...")
            upcoming = await ReminderService.get_upcoming_invoices(days_ahead=settings.upcoming_due_window_days)
            count = len(upcoming)
            summary = f"Found {count} invoice(s) approaching deadline in the next {settings.upcoming_due_window_days} days."

            if count > 0:
                await NotificationService.create_notification(NotificationCreate(
                    type=NotificationType.invoice_deadline,
                    channel=NotificationChannel.in_app,
                    title=f"Upcoming Invoice Deadlines: {count} Invoice(s)",
                    message=f"{count} invoice(s) due within {settings.upcoming_due_window_days} days. Advance reminders prepared for review.",
                    data={"upcoming_count": count},
                ))

            dur = (time.time() - start) * 1000
            await self._log_execution("identify_upcoming_due_invoices", job_name, "success", summary, dur, {"count": count})
            return {"success": True, "count": count, "summary": summary}
        except Exception as e:
            dur = (time.time() - start) * 1000
            err_summary = f"Failure identifying upcoming invoices: {str(e)}"
            logger.error(err_summary)
            await self._log_execution("identify_upcoming_due_invoices", job_name, "failed", err_summary, dur, {"error": str(e)})
            return {"success": False, "error": str(e)}

    async def job_generate_reminder_recommendations(self) -> Dict[str, Any]:
        """Job 3: Generate deduplicated reminder recommendations for review."""
        start = time.time()
        job_name = "Generate Reminder Recommendations"
        try:
            logger.info("Executing scheduled task: Generate Reminder Recommendations...")
            rems = await ReminderService.generate_recommendations(
                days_ahead=settings.upcoming_due_window_days,
                overdue_only=False,
                tone="professional",
            )
            count = len(rems)
            summary = f"Generated {count} personalized reminder recommendation(s) awaiting approval."

            dur = (time.time() - start) * 1000
            await self._log_execution("generate_reminder_recommendations", job_name, "success", summary, dur, {"created_count": count})
            return {"success": True, "count": count, "summary": summary}
        except Exception as e:
            dur = (time.time() - start) * 1000
            err_summary = f"Failure generating reminders: {str(e)}"
            logger.error(err_summary)
            await self._log_execution("generate_reminder_recommendations", job_name, "failed", err_summary, dur, {"error": str(e)})
            return {"success": False, "error": str(e)}

    async def job_refresh_financial_summaries(self) -> Dict[str, Any]:
        """Job 4: Refresh financial intelligence metrics and run anomaly detection."""
        start = time.time()
        job_name = "Refresh Financial Summaries & Anomalies"
        try:
            logger.info("Executing scheduled task: Refresh Financial Summaries...")
            analysis = await FinancialIntelligenceService.get_comprehensive_analysis()
            anomalies = await AnomalyDetectionService.detect_all_anomalies()
            anom_count = anomalies.get("anomalies_detected", 0)

            summary = f"Financial cache refreshed. MoM growth: {analysis['mom_comparison']['growth_rate_pct']}%. Anomalies detected: {anom_count}."

            if anom_count > 0:
                await NotificationService.create_notification(NotificationCreate(
                    type=NotificationType.anomaly,
                    channel=NotificationChannel.in_app,
                    title=f"Financial Anomalies Detected ({anom_count})",
                    message=anomalies.get("summary", "New anomalies flagged for review."),
                    data={"anomalies_count": anom_count},
                ))

            dur = (time.time() - start) * 1000
            await self._log_execution("refresh_financial_summaries", job_name, "success", summary, dur, {
                "monthly_revenue": analysis.get("monthly_revenue"),
                "anomalies_count": anom_count,
            })
            return {"success": True, "summary": summary}
        except Exception as e:
            dur = (time.time() - start) * 1000
            err_summary = f"Failure refreshing summaries: {str(e)}"
            logger.error(err_summary)
            await self._log_execution("refresh_financial_summaries", job_name, "failed", err_summary, dur, {"error": str(e)})
            return {"success": False, "error": str(e)}

    async def job_reconcile_pending_transactions(self) -> Dict[str, Any]:
        """Job 5: Detect pending transactions requiring reconciliation."""
        start = time.time()
        job_name = "Reconcile Pending Transactions"
        try:
            logger.info("Executing scheduled task: Reconcile Pending Transactions...")
            coll = db_manager.transactions
            # Look for pending transactions
            pending_txns = await coll.find({"status": "pending"}).to_list(100)
            count = len(pending_txns)
            summary = f"Reconciliation scan completed: {count} pending transaction(s) monitored."

            dur = (time.time() - start) * 1000
            await self._log_execution("reconcile_pending_transactions", job_name, "success", summary, dur, {"pending_count": count})
            return {"success": True, "count": count, "summary": summary}
        except Exception as e:
            dur = (time.time() - start) * 1000
            err_summary = f"Failure reconciling transactions: {str(e)}"
            logger.error(err_summary)
            await self._log_execution("reconcile_pending_transactions", job_name, "failed", err_summary, dur, {"error": str(e)})
            return {"success": False, "error": str(e)}

    async def job_cleanup_expired_records(self) -> Dict[str, Any]:
        """Job 6: Clean up expired temporary sessions and stale logs."""
        start = time.time()
        job_name = "Cleanup Expired Records"
        try:
            logger.info("Executing scheduled task: Cleanup Expired Records...")
            # Cleanup old automation logs older than 60 days
            cutoff = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            del_result = await db_manager.automation_logs.delete_many({"executed_at": {"$lt": cutoff}})
            deleted_count = getattr(del_result, "deleted_count", 0)
            summary = f"Maintenance cleanup finished. {deleted_count} archived record(s) purged."

            dur = (time.time() - start) * 1000
            await self._log_execution("cleanup_expired_records", job_name, "success", summary, dur, {"deleted_count": deleted_count})
            return {"success": True, "deleted_count": deleted_count, "summary": summary}
        except Exception as e:
            dur = (time.time() - start) * 1000
            err_summary = f"Failure cleaning records: {str(e)}"
            logger.error(err_summary)
            await self._log_execution("cleanup_expired_records", job_name, "failed", err_summary, dur, {"error": str(e)})
            return {"success": False, "error": str(e)}

    # ---------------------------------------------------------
    # Lifecycle Management
    # ---------------------------------------------------------

    def start(self):
        """Start the APScheduler if not already running."""
        if self.is_running:
            logger.info("APScheduler is already running.")
            return

        tz_str = settings.scheduler_timezone or "UTC"
        self.scheduler = AsyncIOScheduler(timezone=tz_str)

        # Register jobs with appropriate triggers
        self.scheduler.add_job(
            self.job_check_overdue_invoices,
            CronTrigger(hour=0, minute=5, timezone=tz_str),
            id="check_overdue_invoices",
            name="Daily Overdue Invoice Check",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            self.job_identify_upcoming_due_invoices,
            CronTrigger(hour=1, minute=0, timezone=tz_str),
            id="identify_upcoming_due_invoices",
            name="Identify Upcoming Due Invoices",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            self.job_generate_reminder_recommendations,
            CronTrigger(hour=2, minute=0, timezone=tz_str),
            id="generate_reminder_recommendations",
            name="Generate Reminder Recommendations",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            self.job_refresh_financial_summaries,
            IntervalTrigger(hours=2),
            id="refresh_financial_summaries",
            name="Refresh Financial Summaries & Anomalies",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            self.job_reconcile_pending_transactions,
            IntervalTrigger(hours=3),
            id="reconcile_pending_transactions",
            name="Reconcile Pending Transactions",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        self.scheduler.add_job(
            self.job_cleanup_expired_records,
            CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=tz_str),
            id="cleanup_expired_records",
            name="Weekly Stale Records Cleanup",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

        try:
            self.scheduler.start()
            self.is_running = True
            logger.info(f"PayPilot APScheduler successfully started in timezone '{tz_str}' with 6 registered background jobs.")
        except Exception as e:
            logger.error(f"Failed to start APScheduler: {e}")
            self.is_running = False

    def shutdown(self, wait: bool = False):
        """Safely terminate scheduler on app shutdown."""
        if self.scheduler and self.is_running:
            logger.info("Shutting down PayPilot APScheduler...")
            self.scheduler.shutdown(wait=wait)
            self.is_running = False
            logger.info("PayPilot APScheduler shutdown complete.")

    def get_status(self) -> Dict[str, Any]:
        """Return list of registered jobs and runtimes."""
        jobs_info = []
        if self.scheduler:
            for j in self.scheduler.get_jobs():
                next_run = j.next_run_time.isoformat() if j.next_run_time else None
                jobs_info.append({
                    "id": j.id,
                    "name": j.name,
                    "trigger": str(j.trigger),
                    "next_run_time": next_run,
                    "is_active": True,
                    "description": j.name,
                })

        return {
            "scheduler_running": self.is_running,
            "timezone": settings.scheduler_timezone or "UTC",
            "jobs": jobs_info,
            "total_jobs": len(jobs_info),
        }

    async def trigger_job_now(self, job_id: str) -> Dict[str, Any]:
        """Manually trigger a registered background job immediately."""
        job_dispatch = {
            "check_overdue_invoices": self.job_check_overdue_invoices,
            "identify_upcoming_due_invoices": self.job_identify_upcoming_due_invoices,
            "generate_reminder_recommendations": self.job_generate_reminder_recommendations,
            "refresh_financial_summaries": self.job_refresh_financial_summaries,
            "reconcile_pending_transactions": self.job_reconcile_pending_transactions,
            "cleanup_expired_records": self.job_cleanup_expired_records,
        }
        if job_id not in job_dispatch:
            return {"success": False, "error": f"Unknown job_id '{job_id}'"}
        return await job_dispatch[job_id]()


scheduler_manager = SchedulerService()

