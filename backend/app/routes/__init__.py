from app.routes.health import router as health_router
from app.routes.customers import router as customers_router
from app.routes.invoices import router as invoices_router
from app.routes.transactions import router as transactions_router
from app.routes.reminders import router as reminders_router
from app.routes.dashboard import router as dashboard_router
from app.routes.chat import router as chat_router
from app.routes.payments import router as payments_router
from app.routes.ai import router as ai_router
from app.routes.automation import router as automation_router
from app.routes.notifications import router as notifications_router
from app.routes.financial_intelligence import router as financial_intelligence_router

__all__ = [
    "health_router",
    "customers_router",
    "invoices_router",
    "transactions_router",
    "reminders_router",
    "dashboard_router",
    "chat_router",
    "payments_router",
    "ai_router",
    "automation_router",
    "notifications_router",
    "financial_intelligence_router",
]
