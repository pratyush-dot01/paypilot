"""
Context Manager Module for PayPilot AI (Phase 4).
Extracts read-only financial and transactional data from MongoDB
to ground all AI responses in verifiable business records.
"""

from typing import Dict, Any, List, Optional
import logging
from app.services.analytics_service import AnalyticsService
from app.services.invoice_service import InvoiceService
from app.services.transaction_service import TransactionService
from app.services.customer_service import CustomerService
from app.services.reminder_service import ReminderService

logger = logging.getLogger("paypilot.ai.context_manager")

class ContextManager:
    """Provides controlled read-only financial context from MongoDB."""

    @classmethod
    async def get_system_grounding_context(cls) -> Dict[str, Any]:
        """
        Assembles comprehensive financial snapshot to ground LLM prompts.
        """
        try:
            stats = await AnalyticsService.get_dashboard_stats()
        except Exception:
            stats = {"total_revenue": 0.0, "pending_payments": 0.0, "completed_transactions": 0, "overdue_invoices": 0}

        try:
            recent_invoices_resp = await InvoiceService.get_all(limit=10)
            invoices = recent_invoices_resp.get("data", [])
        except Exception:
            invoices = []

        try:
            recent_txns_resp = await TransactionService.get_all(limit=10)
            transactions = recent_txns_resp.get("data", [])
        except Exception:
            transactions = []

        try:
            customers_resp = await CustomerService.get_all(limit=10)
            customers = customers_resp.get("data", [])
        except Exception:
            customers = []

        try:
            chart_data = await AnalyticsService.get_revenue_chart()
            monthly_revenue = chart_data.get("data", [])
        except Exception:
            monthly_revenue = []

        # Categorize invoices
        pending_invoices = [i for i in invoices if i.get("status") in {"pending", "overdue"}]
        overdue_invoices = [i for i in invoices if i.get("status") == "overdue"]

        # Customers with outstanding balances
        cust_outstanding: Dict[str, float] = {}
        for inv in pending_invoices:
            cname = inv.get("customer_name") or "Unknown"
            cust_outstanding[cname] = cust_outstanding.get(cname, 0.0) + float(inv.get("total_amount", 0.0))

        return {
            "stats": stats,
            "pending_invoices": [
                {
                    "invoice_number": i.get("invoice_number"),
                    "customer_name": i.get("customer_name"),
                    "total_amount": float(i.get("total_amount", 0)),
                    "due_date": i.get("due_date"),
                    "status": i.get("status"),
                }
                for i in pending_invoices[:8]
            ],
            "overdue_invoices": [
                {
                    "invoice_number": i.get("invoice_number"),
                    "customer_name": i.get("customer_name"),
                    "total_amount": float(i.get("total_amount", 0)),
                    "due_date": i.get("due_date"),
                }
                for i in overdue_invoices[:8]
            ],
            "recent_transactions": [
                {
                    "transaction_id": t.get("id"),
                    "invoice_id": t.get("invoice_id"),
                    "amount": float(t.get("amount", 0)),
                    "currency": t.get("currency", "INR"),
                    "status": t.get("status"),
                    "date": t.get("date"),
                    "payment_method": t.get("payment_method"),
                }
                for t in transactions[:5]
            ],
            "customers_with_balances": [
                {"customer_name": name, "outstanding_amount": round(amt, 2)}
                for name, amt in cust_outstanding.items()
            ],
            "monthly_performance": monthly_revenue[-3:] if monthly_revenue else [],
        }

    @classmethod
    async def get_overdue_invoices(cls) -> List[Dict[str, Any]]:
        """Retrieve all currently overdue invoices."""
        res = await InvoiceService.get_all(status="overdue", limit=50)
        return res.get("data", [])

    @classmethod
    async def get_pending_invoices(cls) -> List[Dict[str, Any]]:
        """Retrieve all pending and overdue invoices."""
        res = await InvoiceService.get_all(status="pending", limit=50)
        pending = res.get("data", [])
        overdue_res = await InvoiceService.get_all(status="overdue", limit=50)
        return pending + overdue_res.get("data", [])

    @classmethod
    async def get_recent_transactions(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent transactions."""
        res = await TransactionService.get_all(limit=limit)
        return res.get("data", [])

    @classmethod
    async def get_customers_with_outstanding(cls) -> List[Dict[str, Any]]:
        """List customers who have unpaid balances."""
        invoices = await cls.get_pending_invoices()
        balances: Dict[str, Dict[str, Any]] = {}
        for inv in invoices:
            cname = inv.get("customer_name") or "Unknown"
            if cname not in balances:
                balances[cname] = {
                    "customer_name": cname,
                    "customer_email": inv.get("customer_email"),
                    "outstanding_amount": 0.0,
                    "invoice_count": 0,
                    "invoices": [],
                }
            balances[cname]["outstanding_amount"] += float(inv.get("total_amount", 0))
            balances[cname]["invoice_count"] += 1
            balances[cname]["invoices"].append(inv.get("invoice_number"))

        return sorted(list(balances.values()), key=lambda x: x["outstanding_amount"], reverse=True)

    @classmethod
    async def get_monthly_comparison(cls) -> Dict[str, Any]:
        """Compare latest month with previous month."""
        chart_res = await AnalyticsService.get_revenue_chart()
        months = chart_res.get("data", [])
        if len(months) >= 2:
            prev_m = months[-2]
            curr_m = months[-1]
            diff = curr_m["revenue"] - prev_m["revenue"]
            pct = (diff / prev_m["revenue"] * 100) if prev_m["revenue"] > 0 else 0
            return {
                "current_month": curr_m["month"],
                "current_revenue": curr_m["revenue"],
                "previous_month": prev_m["month"],
                "previous_revenue": prev_m["revenue"],
                "difference": diff,
                "percentage_change": round(pct, 1),
                "is_positive": diff >= 0,
            }
        elif len(months) == 1:
            return {
                "current_month": months[0]["month"],
                "current_revenue": months[0]["revenue"],
                "previous_month": "N/A",
                "previous_revenue": 0.0,
                "difference": months[0]["revenue"],
                "percentage_change": 100.0,
                "is_positive": True,
            }
        return {}

