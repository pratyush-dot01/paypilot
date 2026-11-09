import logging
import math
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List
from app.core.config import settings
from app.database import db_manager
from app.utils.calculations import to_decimal
from app.models.schemas import (
    AnomalyType,
    AnomalySeverity,
    FinancialAnomaly,
    AnomalyDetectionResponse,
)

logger = logging.getLogger("paypilot.anomalies")


class AnomalyDetectionService:
    @classmethod
    async def detect_all_anomalies(cls) -> Dict[str, Any]:
        """
        Run transparent rule-based statistical anomaly checks across transactions,
        invoices, and customer records.
        """
        now = datetime.now(timezone.utc).isoformat()
        anomalies: List[Dict[str, Any]] = []

        # Load records
        txns = await db_manager.transactions.find({}).to_list(1000)
        invoices = await db_manager.invoices.find({}).to_list(1000)
        customers = await db_manager.customers.find({}).to_list(500)

        # -------------------------------------------------------------
        # Rule 1: Unusually Large Transactions
        # -------------------------------------------------------------
        completed_txns = [t for t in txns if t.get("status") == "completed"]
        if len(completed_txns) >= 3:
            amounts = [float(to_decimal(t.get("amount", 0))) for t in completed_txns]
            mean_amt = sum(amounts) / len(amounts)
            variance = sum((x - mean_amt) ** 2 for x in amounts) / len(amounts)
            std_dev = math.sqrt(variance)

            # Threshold: mean + 2.5 * std_dev or 2.5x mean
            threshold = max(mean_amt + 2.0 * std_dev, mean_amt * settings.anomaly_large_tx_multiplier)

            for t in completed_txns:
                amt = float(to_decimal(t.get("amount", 0)))
                if amt > threshold and amt > 50000.0:
                    anomalies.append({
                        "anomaly_id": f"anom_large_tx_{t.get('id')}",
                        "type": AnomalyType.unusually_large_transaction.value,
                        "severity": AnomalySeverity.medium.value if amt < threshold * 1.5 else AnomalySeverity.high.value,
                        "title": f"Unusually Large Transaction: ₹{amt:,.2f}",
                        "description": f"Transaction {t.get('id')} of ₹{amt:,.2f} is significantly higher than the average volume of ₹{mean_amt:,.2f}.",
                        "explanation": (
                            f"This transaction exceeds {settings.anomaly_large_tx_multiplier}x the typical transaction size. "
                            f"While likely legitimate corporate billing, verify that the delivery and invoicing terms match the order."
                        ),
                        "metrics": {
                            "transaction_id": t.get("id"),
                            "amount": amt,
                            "average_transaction": round(mean_amt, 2),
                            "threshold": round(threshold, 2),
                        },
                        "advisory_only": True,
                        "detected_at": now,
                    })

        # -------------------------------------------------------------
        # Rule 2: Repeated Failed Payments
        # -------------------------------------------------------------
        failed_by_invoice: Dict[str, int] = {}
        for t in txns:
            if t.get("status") == "failed":
                inv_id = t.get("invoice_id", "unknown")
                failed_by_invoice[inv_id] = failed_by_invoice.get(inv_id, 0) + 1

        for inv_id, count in failed_by_invoice.items():
            if count >= 2:
                anomalies.append({
                    "anomaly_id": f"anom_failed_pay_{inv_id}",
                    "type": AnomalyType.repeated_failed_payments.value,
                    "severity": AnomalySeverity.high.value,
                    "title": f"Repeated Failed Payments ({count} attempts) for {inv_id}",
                    "description": f"Invoice {inv_id} has experienced {count} failed payment attempts.",
                    "explanation": (
                        f"Multiple payment failures indicate card declines, insufficient funds, or gateway gateway communication issues. "
                        f"Recommend contacting the customer with an alternate PayPal checkout link or checking bank authorization."
                    ),
                    "metrics": {"invoice_id": inv_id, "failed_attempts": count},
                    "advisory_only": True,
                    "detected_at": now,
                })

        # -------------------------------------------------------------
        # Rule 3: Customers With Frequently Overdue Invoices
        # -------------------------------------------------------------
        cust_invoices: Dict[str, List[Dict[str, Any]]] = {}
        for inv in invoices:
            c_name = inv.get("customer_name") or inv.get("client") or "Unknown"
            cust_invoices.setdefault(c_name, []).append(inv)

        for c_name, inv_list in cust_invoices.items():
            overdue_count = sum(1 for i in inv_list if i.get("status") == "overdue")
            total_count = len(inv_list)
            if total_count >= 2 and overdue_count >= 2:
                late_pct = round((overdue_count / total_count) * 100, 1)
                total_overdue_amt = sum(float(to_decimal(i.get("total_amount") or i.get("amount", 0))) for i in inv_list if i.get("status") == "overdue")
                anomalies.append({
                    "anomaly_id": f"anom_late_cust_{abs(hash(c_name)) % 100000}",
                    "type": AnomalyType.frequent_late_payer.value,
                    "severity": AnomalySeverity.high.value if overdue_count >= 3 else AnomalySeverity.medium.value,
                    "title": f"Frequent Late Payer: {c_name} ({late_pct}% overdue)",
                    "description": f"{c_name} has {overdue_count} of {total_count} invoices overdue, totaling ₹{total_overdue_amt:,.2f}.",
                    "explanation": (
                        f"{c_name} exhibits a recurring delay pattern. Recommend requiring partial advance payments "
                        f"or scheduling proactive reminder notices 3 days prior to due dates."
                    ),
                    "metrics": {
                        "customer_name": c_name,
                        "overdue_invoices": overdue_count,
                        "total_invoices": total_count,
                        "late_payment_ratio_pct": late_pct,
                        "total_overdue_amount": total_overdue_amt,
                    },
                    "advisory_only": True,
                    "detected_at": now,
                })

        # -------------------------------------------------------------
        # Rule 4: Sudden Revenue Drop / Billing Inactivity
        # -------------------------------------------------------------
        today_date = date.today()
        fifteen_days_ago = today_date - timedelta(days=15)
        recent_txns = [t for t in completed_txns if t.get("created_date", "") >= fifteen_days_ago.isoformat()]
        recent_revenue = sum(float(to_decimal(t.get("amount", 0))) for t in recent_txns)

        if len(completed_txns) > 5 and recent_revenue < 25000.0:
            anomalies.append({
                "anomaly_id": "anom_rev_drop_recent",
                "type": AnomalyType.sudden_revenue_drop.value,
                "severity": AnomalySeverity.medium.value,
                "title": "Low 15-Day Revenue Pace",
                "description": f"Completed revenue in the last 15 days is ₹{recent_revenue:,.2f}, lower than typical bi-weekly pace.",
                "explanation": (
                    "Inflow velocity has slowed over the past 15 days. "
                    "Review pending draft invoices and issue follow-up payment links to accelerate collections."
                ),
                "metrics": {"recent_15_day_revenue": recent_revenue},
                "advisory_only": True,
                "detected_at": now,
            })

        summary = (
            f"Detected {len(anomalies)} financial anomalies across transaction volume, payment retries, and customer aging. "
            f"All findings are advisory; manual review recommended."
        )

        return {
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "summary": summary,
            "generated_at": now,
        }

