import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.services.scheduler_service import scheduler_manager
from app.routes import (
    health_router,
    customers_router,
    invoices_router,
    transactions_router,
    reminders_router,
    dashboard_router,
    chat_router,
    payments_router,
    ai_router,
    automation_router,
    notifications_router,
    financial_intelligence_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("paypilot")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup
    logger.info("Initializing PayPilot Backend & Database...")
    await connect_to_mongo()
    if settings.scheduler_enabled:
        scheduler_manager.start()
    yield
    # App shutdown
    logger.info("Shutting down PayPilot Backend...")
    if settings.scheduler_enabled:
        scheduler_manager.shutdown(wait=False)
    await close_mongo_connection()

app = FastAPI(
    title="PayPilot API",
    description=(
        "**PayPilot** — AI-powered payment and business assistant backend.\n\n"
        "### Features:\n"
        "- **Customer Management**: Full CRUD operations for customer records\n"
        "- **Invoice Management**: Automatic numbering (`INV-YYYY-XXXX`), Decimal calculations, and dynamic overdue detection\n"
        "- **Transaction Management**: Payment records with invoice associations\n"
        "- **Dashboard Analytics**: Real-time revenue, overdue counts, monthly statistics\n"
        "- **Reminder Management**: Automated and scheduled payment reminders\n"
        "- **AI Assistant**: Grounded AI agent with LLM + tool calling (Phase 4-6)\n"
        "- **PayPal Integration**: OAuth2, Order creation, capture, webhooks\n"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs" if True else None,  # Disable in production via env check
    redoc_url="/redoc",
)

# CORS Middleware — restrict to configured origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.cors_origins_list else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
)

# Register API Routers
app.include_router(health_router)
app.include_router(customers_router)
app.include_router(invoices_router)
app.include_router(transactions_router)
app.include_router(reminders_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(payments_router)
app.include_router(ai_router)
app.include_router(automation_router)
app.include_router(notifications_router)
app.include_router(financial_intelligence_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
