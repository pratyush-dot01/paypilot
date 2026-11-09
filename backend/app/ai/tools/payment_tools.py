"""
Payment Tools for PayPilot AI Agent (Phase 5).
Interacts directly with PaymentService and PayPal REST API.
Enforces mandatory user confirmation before generating PayPal orders/links.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.payment_service import PaymentService
from app.services.paypal_service import PayPalService
from app.services.invoice_service import InvoiceService

class CreatePayPalOrderInput(BaseModel):
    invoice_id: str = Field(..., description="The ID (inv_...) or invoice number (INV-2026-...) of the invoice to generate a PayPal payment link for")

class CreatePayPalOrderTool(BaseTool):
    name = "create_paypal_order"
    description = "Generate an official PayPal Sandbox order and customer approval link for an unpaid invoice. SENSITIVE: Requires explicit user confirmation."
    input_schema = CreatePayPalOrderInput
    requires_confirmation = True

    async def run(self, invoice_id: str) -> Dict[str, Any]:
        # Validate invoice exists server-side
        inv = await InvoiceService.get_invoice_by_id(invoice_id)
        if not inv:
            return {"success": False, "error": f"Invoice '{invoice_id}' not found in database"}

        if inv.get("status") == "paid":
            return {"success": False, "error": f"Invoice '{inv.get('invoice_number', invoice_id)}' is already paid"}

        # Call real PaymentService
        result = await PaymentService.create_paypal_order(inv["id"])
        return {
            "success": True,
            "order_id": result["order_id"],
            "approval_url": result.get("approval_url"),
            "invoice_id": result["invoice_id"],
            "invoice_number": result["invoice_number"],
            "amount": result["amount"],
            "currency": result["currency"],
            "status": result["status"],
            "mode": result.get("mode", "sandbox"),
        }

class GetPaymentStatusInput(BaseModel):
    invoice_id: Optional[str] = Field(None, description="Invoice ID or invoice number")
    order_id: Optional[str] = Field(None, description="PayPal Order ID if available")

class GetPaymentStatusTool(BaseTool):
    name = "get_payment_status"
    description = "Retrieve current payment settlement status from PayPal and database for an invoice or order."
    input_schema = GetPaymentStatusInput

    async def run(
        self,
        invoice_id: Optional[str] = None,
        order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if invoice_id:
            inv = await InvoiceService.get_invoice_by_id(invoice_id)
            if not inv:
                return {"found": False, "error": f"Invoice '{invoice_id}' not found"}

            payment_info = await PaymentService.get_invoice_payment_info(inv["id"])
            return {
                "found": True,
                "invoice_id": inv["id"],
                "invoice_number": inv.get("invoice_number"),
                "status": inv.get("status"),
                "is_paid": payment_info.get("is_paid", inv.get("status") == "paid"),
                "amount": inv.get("total_amount"),
                "currency": inv.get("currency", "INR"),
                "paypal_order_id": inv.get("paypal_order_id"),
                "transactions_count": len(payment_info.get("transactions", [])),
            }

        if order_id:
            try:
                order_details = await PayPalService.get_order_details(order_id)
                return {
                    "found": True,
                    "order_id": order_id,
                    "status": order_details.get("status"),
                    "intent": order_details.get("intent"),
                    "create_time": order_details.get("create_time"),
                }
            except Exception as e:
                return {"found": False, "error": f"Failed to retrieve PayPal order: {str(e)}"}

        return {"found": False, "error": "Either invoice_id or order_id must be provided"}

class GetPaymentDetailsInput(BaseModel):
    invoice_id: str = Field(..., description="Invoice ID or invoice number")

class GetPaymentDetailsTool(BaseTool):
    name = "get_payment_details"
    description = "Retrieve complete payment ledger details and transaction associations for an invoice."
    input_schema = GetPaymentDetailsInput

    async def run(self, invoice_id: str) -> Dict[str, Any]:
        inv = await InvoiceService.get_invoice_by_id(invoice_id)
        if not inv:
            return {"found": False, "error": f"Invoice '{invoice_id}' not found"}

        payment_info = await PaymentService.get_invoice_payment_info(inv["id"])
        return {
            "found": True,
            "invoice_id": inv["id"],
            "invoice_number": inv.get("invoice_number"),
            "customer_name": inv.get("customer_name"),
            "amount": inv.get("total_amount"),
            "currency": inv.get("currency", "INR"),
            "status": inv.get("status"),
            "paypal_order_id": inv.get("paypal_order_id"),
            "transactions": payment_info.get("transactions", []),
        }
