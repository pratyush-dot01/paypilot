from fastapi import APIRouter, HTTPException, status
from app.models.schemas import HealthResponse
from app.core.config import settings
from app.database import db_manager

router = APIRouter(tags=["System Health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint indicating API operational status and MongoDB connectivity."""
    if settings.environment.lower() == "production" and not db_manager.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unreachable in production mode."
        )

    db_status = "connected" if db_manager.is_connected else ("in-memory (mock)" if db_manager.is_mock else "disconnected")

    cust_count = await db_manager.customers.count_documents({})
    inv_count = await db_manager.invoices.count_documents({})
    txn_count = await db_manager.transactions.count_documents({})
    rem_count = await db_manager.reminders.count_documents({})

    return HealthResponse(
        status="ok",
        version="2.0.0",
        environment=settings.environment,
        database=db_status,
        collections={
            "customers": cust_count,
            "invoices": inv_count,
            "transactions": txn_count,
            "reminders": rem_count,
        }
    )

@router.get("/")
async def root():
    return {
        "name": "PayPilot API",
        "description": "AI-powered payment and business assistant backend",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }
