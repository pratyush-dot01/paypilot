"""
Analytics Tools for PayPilot AI Agent (Phase 5).
Interacts directly with AnalyticsService and TransactionService to compute cash flow,
aggregations, pending receivables, and transaction histories.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.analytics_service import AnalyticsService
from app.services.transaction_service import TransactionService
from app.services.invoice_service import InvoiceService

class EmptyInput(BaseModel):
    pass

class GetRevenueSummaryTool(BaseTool):
    name = "get_revenue_summary"
    description = "Retrieve high-level business analytics: total revenue collected, pending payments, completed transactions, overdue count, and monthly trajectory."
    input_schema = EmptyInput

    async def run(self) -> Dict[str, Any]:
        stats = await AnalyticsService.get_dashboard_stats()
        chart = await AnalyticsService.get_revenue_chart()
        months = chart.get("data", [])
        return {
            "total_revenue": stats.get("total_revenue", 0.0),
            "pending_payments": stats.get("pending_payments", 0.0),
            "completed_transactions": stats.get("completed_transactions", 0),
            "overdue_invoices": stats.get("overdue_invoices", 0),
            "recent_monthly_performance": months[-3:] if months else [],
        }

class GetPendingPaymentsTool(BaseTool):
    name = "get_pending_payments"
    description = "Retrieve list and sum of all unpaid pending customer invoices awaiting settlement."
    input_schema = EmptyInput

    async def run(self) -> Dict[str, Any]:
        pending_res = await InvoiceService.get_invoices(status="pending", limit=50)
        overdue_res = await InvoiceService.get_invoices(status="overdue", limit=50)
        all_unpaid = pending_res.get("data", []) + overdue_res.get("data", [])

        total_pending = sum(float(i.get("total_amount", 0)) for i in all_unpaid)
        return {
            "count": len(all_unpaid),
            "total_pending_amount": round(total_pending, 2),
            "unpaid_invoices": [
                {
                    "invoice_id": i["id"],
                    "invoice_number": i.get("invoice_number"),
                    "customer_name": i.get("customer_name"),
                    "total_amount": i.get("total_amount"),
                    "currency": i.get("currency", "INR"),
                    "status": i.get("status"),
                    "due_date": i.get("due_date"),
                }
                for i in all_unpaid[:10]
            ],
        }

class GetTransactionHistoryInput(BaseModel):
    limit: Optional[int] = Field(5, ge=1, le=50, description="Max transactions to return")
    status: Optional[str] = Field(None, description="Filter by status: 'completed', 'pending', 'failed'")

class GetTransactionHistoryTool(BaseTool):
    name = "get_transaction_history"
    description = "Retrieve verified transaction ledger history, credits, and debits."
    input_schema = GetTransactionHistoryInput

    async def run(
        self,
        limit: int = 5,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        res = await TransactionService.get_all(limit=limit, status=status)
        txns = res.get("data", [])
        return {
            "count": len(txns),
            "transactions": [
                {
                    "transaction_id": t["id"],
                    "invoice_id": t.get("invoice_id"),
                    "amount": t.get("amount"),
                    "currency": t.get("currency", "INR"),
                    "status": t.get("status"),
                    "payment_method": t.get("payment_method"),
                    "date": t.get("date"),
                }
                for t in txns
            ],
        }

