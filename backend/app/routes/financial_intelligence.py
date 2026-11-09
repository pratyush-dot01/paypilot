from fastapi import APIRouter, Query
from typing import Dict, Any, Optional
from app.services.financial_intelligence_service import FinancialIntelligenceService
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/api/analytics", tags=["Financial Intelligence & Anomalies"])


@router.get("/financial-intelligence")
async def get_financial_intelligence():
    """
    Retrieve comprehensive financial intelligence:
    - Daily, weekly, monthly actual revenue
    - Month-over-month (MoM) revenue comparison & explanation
    - Algorithmic revenue forecast (explicitly marked as estimated)
    - Customer payment behavior & risk classification
    - Transaction momentum trends
    """
    return await FinancialIntelligenceService.get_comprehensive_analysis()


@router.get("/anomalies")
async def get_detected_anomalies():
    """
    Retrieve transparent rule-based statistical anomaly findings:
    - Unusually large transactions
    - Sudden revenue drops
    - Repeated payment failures
    - Frequent late-paying customers
    All findings are advisory and explained in plain English.
    """
    return await AnomalyDetectionService.detect_all_anomalies()


@router.get("/upcoming-deadlines")
async def get_upcoming_deadlines(days: int = Query(7, ge=1, le=30)):
    """Retrieve unpaid invoices due in the next N days for automation dashboards."""
    invoices = await ReminderService.get_upcoming_invoices(days_ahead=days)
    return {"data": invoices, "total": len(invoices), "days_ahead": days}

