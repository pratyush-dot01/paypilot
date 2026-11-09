from fastapi import APIRouter, Request, HTTPException, status
from typing import Dict, Any
from app.core.config import settings
from app.models.schemas import (
    CreateOrderRequest,
    CreateOrderResponse,
    CaptureOrderRequest,
    CaptureOrderResponse,
    PayPalConfigResponse,
    WebhookResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/api/payments", tags=["PayPal Payments"])

@router.get("/config", response_model=PayPalConfigResponse)
async def get_paypal_config():
    """
    Public PayPal configuration endpoint for frontend SDK initialization.
    Safely provides client_id and environment without exposing secrets or access tokens.
    """
    return PayPalConfigResponse(
        client_id=settings.paypal_client_id,
        currency=settings.default_currency,
        mode=settings.paypal_mode,
        is_live=(settings.paypal_mode == "live"),
    )

@router.post("/create-order", response_model=CreateOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_order(payload: CreateOrderRequest):
    """
    Create a PayPal order for an existing invoice.
    Retrieves trusted amount and currency directly from MongoDB.
    Associates the created PayPal order ID with the invoice.
    """
    return await PaymentService.create_paypal_order(payload.invoice_id)

@router.post("/capture-order", response_model=CaptureOrderResponse)
async def capture_payment_order(payload: CaptureOrderRequest):
    """
    Capture an approved PayPal payment order.
    Validates association, records completed transaction, and transitions invoice to 'paid'.
    Provides idempotency protection against duplicate captures.
    """
    return await PaymentService.capture_paypal_order(
        order_id=payload.order_id,
        invoice_id=payload.invoice_id,
    )

@router.get("/order/{order_id}")
async def get_order_details(order_id: str):
    """
    Retrieve live PayPal order details and database invoice association.
    """
    return await PaymentService.get_order_details(order_id)

@router.get("/invoice/{invoice_id}")
async def get_invoice_payment_info(invoice_id: str):
    """
    Retrieve payment status and transaction history for an invoice.
    """
    return await PaymentService.get_invoice_payment_info(invoice_id)

@router.post("/webhook", response_model=WebhookResponse)
async def handle_paypal_webhook(request: Request):
    """
    PayPal Webhook endpoint.
    Verifies transmission signature and processes events with idempotency.
    """
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON webhook payload")

    res = await PaymentService.handle_webhook_event(headers, raw_body)
    return WebhookResponse(
        status=res.get("status", "success"),
        event_type=res.get("event_type", "UNKNOWN"),
        event_id=res.get("event_id", ""),
        message=res.get("message", "Processed"),
    )

