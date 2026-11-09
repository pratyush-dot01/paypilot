from fastapi import APIRouter
from app.models.schemas import DashboardStats, RevenueChartResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard Analytics"])

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """
    Retrieve real-time dashboard analytics KPIs:
    - Total revenue
    - Pending payments
    - Completed transactions count
    - Overdue invoice count
    """
    return await AnalyticsService.get_dashboard_stats()

@router.get("/revenue-chart", response_model=RevenueChartResponse)
async def get_revenue_chart():
    """Retrieve 12-month revenue vs expenses data for analytics charts."""
    data = await AnalyticsService.get_revenue_chart()
    return {"data": data}

@router.get("/recent-transactions")
async def get_recent_transactions():
    """Retrieve latest transactions for the dashboard table."""
    data = await AnalyticsService.get_recent_transactions(limit=7)
    return {"data": data}
