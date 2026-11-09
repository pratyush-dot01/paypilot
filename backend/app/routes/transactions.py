from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from app.models.schemas import TransactionCreate, TransactionResponse
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/transactions", tags=["Transaction Management"])

@router.get("/")
async def get_transactions(
    status: Optional[str] = Query(None, description="Filter by status: completed, pending, failed"),
    type: Optional[str] = Query(None, description="Filter by type: credit, debit"),
    invoice_id: Optional[str] = Query(None, description="Filter by associated invoice ID"),
    search: Optional[str] = Query(None, description="Search by name, category, or ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Retrieve all transactions with optional filtering and pagination."""
    return await TransactionService.get_transactions(
        status=status,
        type=type,
        invoice_id=invoice_id,
        search=search,
        limit=limit,
        offset=offset,
    )

@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(payload: TransactionCreate):
    """
    Record a new transaction.
    Associates with an invoice if invoice_id is provided.
    Note: Does NOT mark invoice as paid (reserved for PayPal confirmation in Phase 3).
    """
    return await TransactionService.create_transaction(payload)

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: str):
    """Retrieve a specific transaction by ID."""
    txn = await TransactionService.get_transaction_by_id(transaction_id)
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID '{transaction_id}' not found",
        )
    return txn
