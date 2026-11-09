"""
Invoice Tools for PayPilot AI Agent (Phase 5).
Interacts directly with InvoiceService to create, query, list, and update invoices.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.ai.tools.base import BaseTool
from app.services.invoice_service import InvoiceService
from app.models.schemas import InvoiceCreate, InvoiceUpdate, InvoiceItem, InvoiceStatus

class CreateInvoiceInput(BaseModel):
    customer_name: str = Field(..., description="Customer or business name")
    amount: float = Field(..., gt=0, description="Pre-tax subtotal or unit price")
    description: Optional[str] = Field("Professional Services", description="Invoice description or service performed")
    currency: Optional[str] = Field("INR", description="Currency code (e.g. INR, USD, EUR)")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format. Defaults to 14 days from today.")
    customer_id: Optional[str] = Field(None, description="Optional customer ID if known")
    tax_rate: Optional[float] = Field(18.0, ge=0, description="Tax percentage rate (e.g. 18.0 for 18% GST)")

class CreateInvoiceTool(BaseTool):
    name = "create_invoice"
    description = "Create a new real invoice in the database with automatic sequential numbering, 18% GST tax calculation, and overdue tracking."
    input_schema = CreateInvoiceInput
    requires_confirmation = False

    async def run(
        self,
        customer_name: str,
        amount: float,
        description: str = "Professional Services",
        currency: str = "INR",
        due_date: Optional[str] = None,
        customer_id: Optional[str] = None,
        tax_rate: float = 18.0,
    ) -> Dict[str, Any]:
        if not due_date:
            due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

        item = InvoiceItem(
            description=description,
            quantity=1,
            unit_price=amount,
        )
        payload = InvoiceCreate(
            customer_id=customer_id or f"cust_{customer_name.lower().replace(' ', '_')[:10]}",
            customer_name=customer_name,
            description=description,
            items=[item],
            tax_rate=tax_rate,
            currency=currency.upper(),
            due_date=due_date,
            status=InvoiceStatus.pending,
        )
        created = await InvoiceService.create_invoice(payload)
        return {
            "invoice_id": created["id"],
            "invoice_number": created["invoice_number"],
            "customer_name": created["customer_name"],
            "subtotal": created["subtotal"],
            "tax": created["tax"],
            "total_amount": created["total_amount"],
            "currency": created["currency"],
            "due_date": created["due_date"],
            "status": created["status"],
        }

class GetInvoiceInput(BaseModel):
    invoice_id: str = Field(..., description="The unique invoice ID (e.g. inv_...) or sequential invoice number (e.g. INV-2026-0001)")

class GetInvoiceTool(BaseTool):
    name = "get_invoice"
    description = "Retrieve full invoice details, line items, status, and amounts by invoice ID or invoice number."
    input_schema = GetInvoiceInput

    async def run(self, invoice_id: str) -> Dict[str, Any]:
        inv = await InvoiceService.get_invoice_by_id(invoice_id)
        if not inv:
            return {"found": False, "message": f"Invoice '{invoice_id}' not found"}
        return {
            "found": True,
            "invoice_id": inv["id"],
            "invoice_number": inv.get("invoice_number"),
            "customer_name": inv.get("customer_name"),
            "description": inv.get("description"),
            "subtotal": inv.get("subtotal"),
            "tax": inv.get("tax"),
            "total_amount": inv.get("total_amount"),
            "currency": inv.get("currency"),
            "status": inv.get("status"),
            "due_date": inv.get("due_date"),
            "paypal_order_id": inv.get("paypal_order_id"),
        }

class ListInvoicesInput(BaseModel):
    status: Optional[str] = Field(None, description="Optional filter by status: 'draft', 'pending', 'paid', 'overdue'")
    customer_id: Optional[str] = Field(None, description="Optional filter by customer ID")
    search: Optional[str] = Field(None, description="Optional text search for client name, description, or invoice number")
    limit: Optional[int] = Field(10, ge=1, le=50, description="Max invoices to return")

class ListInvoicesTool(BaseTool):
    name = "list_invoices"
    description = "List invoices from the database with optional filtering by status (paid, pending, overdue), customer, or search keyword."
    input_schema = ListInvoicesInput

    async def run(
        self,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        res = await InvoiceService.get_invoices(
            status=status,
            customer_id=customer_id,
            search=search,
            limit=limit,
        )
        invoices = res.get("data", [])
        return {
            "count": len(invoices),
            "total": res.get("total", len(invoices)),
            "invoices": [
                {
                    "invoice_id": i["id"],
                    "invoice_number": i.get("invoice_number"),
                    "customer_name": i.get("customer_name"),
                    "total_amount": i.get("total_amount"),
                    "currency": i.get("currency", "INR"),
                    "status": i.get("status"),
                    "due_date": i.get("due_date"),
                }
                for i in invoices
            ],
        }

class UpdateInvoiceInput(BaseModel):
    invoice_id: str = Field(..., description="Invoice ID or invoice number to update")
    status: Optional[str] = Field(None, description="New status: 'draft', 'pending', 'paid', 'overdue'")
    description: Optional[str] = Field(None, description="New description")
    due_date: Optional[str] = Field(None, description="New due date in YYYY-MM-DD format")

class UpdateInvoiceTool(BaseTool):
    name = "update_invoice"
    description = "Update an existing invoice's status, description, or due date."
    input_schema = UpdateInvoiceInput

    async def run(
        self,
        invoice_id: str,
        status: Optional[str] = None,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        inv = await InvoiceService.get_invoice_by_id(invoice_id)
        if not inv:
            return {"success": False, "message": f"Invoice '{invoice_id}' not found"}

        update_payload = InvoiceUpdate(
            status=InvoiceStatus(status) if status else None,
            description=description,
            due_date=due_date,
        )
        updated = await InvoiceService.update_invoice(inv["id"], update_payload)
        return {
            "success": True,
            "invoice_id": updated["id"],
            "invoice_number": updated.get("invoice_number"),
            "status": updated.get("status"),
            "due_date": updated.get("due_date"),
        }

class FindOverdueInvoicesInput(BaseModel):
    limit: Optional[int] = Field(10, ge=1, le=50, description="Max overdue invoices to return")

class FindOverdueInvoicesTool(BaseTool):
    name = "find_overdue_invoices"
    description = "Find all invoices that have passed their due date and remain unpaid."
    input_schema = FindOverdueInvoicesInput

    async def run(self, limit: int = 10) -> Dict[str, Any]:
        res = await InvoiceService.get_invoices(status="overdue", limit=limit)
        items = res.get("data", [])
        total_overdue = sum(float(i.get("total_amount", 0)) for i in items)
        return {
            "count": len(items),
            "total_overdue_amount": round(total_overdue, 2),
            "overdue_invoices": [
                {
                    "invoice_id": i["id"],
                    "invoice_number": i.get("invoice_number"),
                    "customer_name": i.get("customer_name"),
                    "total_amount": i.get("total_amount"),
                    "currency": i.get("currency", "INR"),
                    "due_date": i.get("due_date"),
                }
                for i in items
            ],
        }

