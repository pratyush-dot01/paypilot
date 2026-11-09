from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from app.models.schemas import InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceSummaryResponse
from app.services.invoice_service import InvoiceService

router = APIRouter(prefix="/api/invoices", tags=["Invoice Management"])

@router.post("/", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(payload: InvoiceCreate):
    """
    Create a new invoice.
    - Automatically generates sequential invoice number (e.g. INV-2026-0001).
    - Calculates subtotal, tax amount, and total amount using precise Decimal arithmetic.
    - Evaluates due date for automatic overdue detection.
    """
    return await InvoiceService.create_invoice(payload)

@router.get("/summary", response_model=InvoiceSummaryResponse)
async def get_invoice_summary():
    """Retrieve aggregate summary of invoices (total, paid, pending, overdue, draft)."""
    return await InvoiceService.get_summary()

@router.get("/")
async def get_invoices(
    status: Optional[str] = Query(None, description="Filter by status: draft, pending, paid, overdue"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    search: Optional[str] = Query(None, description="Search by invoice number or client name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Retrieve all invoices with optional filtering and pagination.
    Performs automatic dynamic overdue status evaluation on retrieval.
    """
    return await InvoiceService.get_invoices(
        status=status,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
        search=search,
    )

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str):
    """Retrieve an invoice by its unique ID or invoice number."""
    inv = await InvoiceService.get_invoice_by_id(invoice_id)
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID or number '{invoice_id}' not found",
        )
    return inv

@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(invoice_id: str, payload: InvoiceUpdate):
    """
    Update an invoice.
    If line items or tax rate are updated, recalculates subtotal, tax, and totals using Decimal.
    """
    updated = await InvoiceService.update_invoice(invoice_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID '{invoice_id}' not found",
        )
    return updated

@router.delete("/{invoice_id}", status_code=status.HTTP_200_OK)
async def delete_invoice(invoice_id: str):
    """Delete an invoice."""
    success = await InvoiceService.delete_invoice(invoice_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID '{invoice_id}' not found",
        )
    return {"message": "Invoice successfully deleted", "id": invoice_id}
