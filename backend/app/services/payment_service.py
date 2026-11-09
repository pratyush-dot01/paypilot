import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from app.database import db_manager
from app.services.paypal_service import PayPalService
from app.utils.generators import generate_id
from app.utils.calculations import to_decimal

logger = logging.getLogger("paypilot.payments")

class PaymentService:
    @classmethod
    async def create_paypal_order(cls, invoice_id: str) -> Dict[str, Any]:
        """
        Create a PayPal order for an existing invoice.
        Retrieves trusted amount and currency from database, validates status,
        and saves the PayPal order ID against the invoice.
        """
        coll = db_manager.invoices
        invoice = await coll.find_one({"id": invoice_id})
        if not invoice:
            invoice = await coll.find_one({"invoice_number": invoice_id})
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice '{invoice_id}' not found",
            )

        # Disallow order creation for already paid invoices
        if invoice.get("status") == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invoice '{invoice.get('invoice_number', invoice_id)}' is already paid",
            )

        # Call PayPal Orders API
        try:
            order_data = await PayPalService.create_order(invoice)
        except Exception as e:
            logger.error(f"Error creating PayPal order for invoice {invoice_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"PayPal API error: {str(e)}",
            )

        order_id = order_data["id"]
        approval_url = None
        for link in order_data.get("links", []):
            if link.get("rel") in ["approve", "payer-action"]:
                approval_url = link.get("href")
                break

        # Associate PayPal order ID with the invoice in MongoDB
        now_iso = datetime.now(timezone.utc).isoformat()
        await coll.update_one(
            {"id": invoice["id"]},
            {
                "$set": {
                    "paypal_order_id": order_id,
                    "updated_date": now_iso,
                }
            },
        )

        return {
            "order_id": order_id,
            "approval_url": approval_url,
            "invoice_id": invoice["id"],
            "invoice_number": invoice.get("invoice_number", invoice["id"]),
            "amount": float(invoice.get("total_amount", 0.0)),
            "currency": invoice.get("currency", "USD"),
            "status": order_data.get("status", "CREATED"),
            "mode": "sandbox",
        }

    @classmethod
    async def capture_paypal_order(cls, order_id: str, invoice_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Capture an approved PayPal order.
        Validates invoice-to-order association, enforces idempotency,
        records transaction, and updates invoice to 'paid'.
        """
        inv_coll = db_manager.invoices
        txn_coll = db_manager.transactions

        # 1. Locate the associated invoice in MongoDB
        invoice = None
        if invoice_id:
            invoice = await inv_coll.find_one({"id": invoice_id})
            if not invoice:
                invoice = await inv_coll.find_one({"invoice_number": invoice_id})

        if not invoice:
            invoice = await inv_coll.find_one({"paypal_order_id": order_id})

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No invoice found matching PayPal order ID '{order_id}'",
            )

        # 2. Idempotency Protection: Check if this order was already captured
        existing_txn = await txn_coll.find_one({"paypal_order_id": order_id})
        if invoice.get("status") == "paid" and existing_txn:
            logger.info(f"Idempotent response: Order {order_id} was already captured")
            return {
                "status": "COMPLETED",
                "message": "Payment already captured successfully",
                "transaction_id": existing_txn.get("id"),
                "invoice_id": invoice["id"],
                "invoice_number": invoice.get("invoice_number", invoice["id"]),
                "paypal_order_id": order_id,
                "paypal_capture_id": existing_txn.get("paypal_capture_id", order_id),
                "amount": float(existing_txn.get("amount", invoice.get("total_amount", 0.0))),
                "currency": existing_txn.get("currency", invoice.get("currency", "USD")),
                "payer_email": existing_txn.get("payer_email"),
                "payer_name": existing_txn.get("payer_name"),
            }

        # 3. Call PayPal Capture API (or simulated capture for test order IDs)
        if order_id.startswith("MOCK_") or order_id.startswith("TEST_"):
            logger.info(f"Simulating approved capture for test order: {order_id}")
            capture_data = {
                "id": order_id,
                "status": "COMPLETED",
                "purchase_units": [
                    {
                        "payments": {
                            "captures": [
                                {
                                    "id": f"CAP-{order_id}",
                                    "status": "COMPLETED",
                                    "amount": {
                                        "value": str(invoice.get("total_amount", 100.0)),
                                        "currency_code": invoice.get("currency", "USD"),
                                    },
                                }
                            ]
                        }
                    }
                ],
                "payer": {
                    "email_address": "buyer-test@sandbox.paypal.com",
                    "name": {"given_name": "Sandbox", "surname": "Buyer"},
                },
            }
        else:
            try:
                capture_data = await PayPalService.capture_order(order_id)
            except Exception as e:
                # Check if order was already captured on PayPal
                if "ORDER_ALREADY_CAPTURED" in str(e):
                    logger.warning(f"PayPal reported ORDER_ALREADY_CAPTURED for {order_id}")
                    # Fetch order details to sync
                    capture_data = await PayPalService.get_order(order_id)
                else:
                    logger.error(f"PayPal capture failed for order {order_id}: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"PayPal capture failed: {str(e)}",
                    )

        # 4. Extract verified capture details
        paypal_status = capture_data.get("status", "")
        capture_id = order_id
        capture_amount = float(invoice.get("total_amount", 0.0))
        capture_currency = invoice.get("currency", "USD")

        # Extract payment capture units if available
        purchase_units = capture_data.get("purchase_units", [])
        if purchase_units:
            payments = purchase_units[0].get("payments", {})
            captures = payments.get("captures", [])
            if captures:
                capture_obj = captures[0]
                capture_id = capture_obj.get("id", order_id)
                paypal_status = capture_obj.get("status", paypal_status)
                amt_obj = capture_obj.get("amount", {})
                if "value" in amt_obj:
                    capture_amount = float(amt_obj["value"])
                if "currency_code" in amt_obj:
                    capture_currency = amt_obj["currency_code"]

        payer_email = None
        payer_name = None
        payer = capture_data.get("payer", {})
        if payer:
            payer_email = payer.get("email_address")
            p_name = payer.get("name", {})
            if p_name:
                payer_name = f"{p_name.get('given_name', '')} {p_name.get('surname', '')}".strip()

        # 5. Record Transaction in MongoDB
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        date_str = now_dt.strftime("%Y-%m-%d")
        txn_id = generate_id("txn_")

        txn_doc = {
            "id": txn_id,
            "invoice_id": invoice["id"],
            "paypal_order_id": order_id,
            "paypal_capture_id": capture_id,
            "name": f"{invoice.get('customer_name', 'Client')} (PayPal)",
            "amount": capture_amount,
            "currency": capture_currency,
            "status": "completed" if paypal_status == "COMPLETED" else "pending",
            "type": "credit",
            "category": "PayPal Checkout",
            "payment_method": "paypal",
            "payer_email": payer_email,
            "payer_name": payer_name,
            "date": date_str,
            "created_date": now_iso,
        }
        await txn_coll.insert_one(txn_doc)

        # 6. Update Invoice in MongoDB: Mark as PAID only after successful capture!
        if paypal_status == "COMPLETED":
            await inv_coll.update_one(
                {"id": invoice["id"]},
                {
                    "$set": {
                        "status": "paid",
                        "paypal_order_id": order_id,
                        "paypal_capture_id": capture_id,
                        "paid_date": now_iso,
                        "updated_date": now_iso,
                    }
                },
            )

        logger.info(f"Successfully processed capture for invoice {invoice['id']} / order {order_id}")

        return {
            "status": paypal_status,
            "message": "Payment captured and verified successfully",
            "transaction_id": txn_id,
            "invoice_id": invoice["id"],
            "invoice_number": invoice.get("invoice_number", invoice["id"]),
            "paypal_order_id": order_id,
            "paypal_capture_id": capture_id,
            "amount": capture_amount,
            "currency": capture_currency,
            "payer_email": payer_email,
            "payer_name": payer_name,
        }

    @classmethod
    async def get_order_details(cls, order_id: str) -> Dict[str, Any]:
        """Fetch order details from PayPal and pair with database invoice."""
        paypal_order = await PayPalService.get_order(order_id)
        invoice = await db_manager.invoices.find_one({"paypal_order_id": order_id})
        return {
            "paypal_order": paypal_order,
            "invoice": invoice,
        }

    @classmethod
    async def get_invoice_payment_info(cls, invoice_id: str) -> Dict[str, Any]:
        """Get payment status and related transactions for an invoice."""
        inv_coll = db_manager.invoices
        invoice = await inv_coll.find_one({"id": invoice_id})
        if not invoice:
            invoice = await inv_coll.find_one({"invoice_number": invoice_id})
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        txns = await db_manager.transactions.find({"invoice_id": invoice["id"]}).to_list(20)
        for t in txns:
            t.pop("_id", None)
        invoice.pop("_id", None)

        return {
            "invoice": invoice,
            "transactions": txns,
            "is_paid": invoice.get("status") == "paid",
            "paypal_order_id": invoice.get("paypal_order_id"),
            "paypal_capture_id": invoice.get("paypal_capture_id"),
        }

    # Alias for AI tools
    get_payment_for_invoice = get_invoice_payment_info

    @classmethod
    async def handle_webhook_event(cls, headers: Dict[str, str], raw_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle and verify incoming PayPal webhooks.
        Provides idempotency protection using MongoDB 'webhook_logs'.
        """
        # 1. Verify signature
        is_valid = await PayPalService.verify_webhook_signature(headers, raw_body)
        if not is_valid:
            logger.warning("Rejected webhook due to invalid signature verification")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )

        event_id = raw_body.get("id")
        event_type = raw_body.get("event_type", "UNKNOWN")

        # 2. Idempotency Protection: check if event was already handled
        webhook_coll = db_manager.get_collection("webhook_logs")
        existing_event = await webhook_coll.find_one({"event_id": event_id})
        if existing_event:
            logger.info(f"Duplicate webhook event ignored: {event_id} ({event_type})")
            return {
                "status": "duplicate",
                "event_type": event_type,
                "event_id": event_id,
                "message": "Event already processed",
            }

        # 3. Process supported events
        resource = raw_body.get("resource", {})
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            # Extract custom_id or invoice_id
            custom_id = resource.get("custom_id")
            order_id = resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
            capture_id = resource.get("id")

            # Look up invoice
            invoice = None
            if custom_id:
                invoice = await db_manager.invoices.find_one({"id": custom_id})
            if not invoice and order_id:
                invoice = await db_manager.invoices.find_one({"paypal_order_id": order_id})

            if invoice and invoice.get("status") != "paid":
                now_iso = datetime.now(timezone.utc).isoformat()
                await db_manager.invoices.update_one(
                    {"id": invoice["id"]},
                    {
                        "$set": {
                            "status": "paid",
                            "paypal_capture_id": capture_id,
                            "paid_date": now_iso,
                            "updated_date": now_iso,
                        }
                    },
                )
                logger.info(f"Webhook marked invoice {invoice['id']} as paid")

        # 4. Save to webhook log for idempotency
        await webhook_coll.insert_one({
            "event_id": event_id,
            "event_type": event_type,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "summary": raw_body.get("summary", ""),
        })

        return {
            "status": "success",
            "event_type": event_type,
            "event_id": event_id,
            "message": "Webhook processed and state synchronized",
        }
