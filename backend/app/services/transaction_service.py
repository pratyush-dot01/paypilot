from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.database import db_manager
from app.models.schemas import TransactionCreate
from app.utils.generators import generate_id
from app.utils.calculations import to_decimal

class TransactionService:
    @staticmethod
    async def get_transactions(
        status: Optional[str] = None,
        type: Optional[str] = None,
        invoice_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        coll = db_manager.transactions
        query = {}
        if status:
            query["status"] = status
        if type:
            query["type"] = type
        if invoice_id:
            query["invoice_id"] = invoice_id

        items = await coll.find(query).skip(offset).limit(limit).to_list(limit)

        if search:
            s_lower = search.lower()
            items = [
                t for t in items
                if s_lower in t.get("name", "").lower()
                or s_lower in t.get("category", "").lower()
                or s_lower in t.get("id", "").lower()
            ]

        total = await coll.count_documents(query)
        for item in items:
            item.pop("_id", None)

        return {"data": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_transaction_by_id(transaction_id: str) -> Optional[Dict[str, Any]]:
        coll = db_manager.transactions
        txn = await coll.find_one({"id": transaction_id})
        if txn:
            txn.pop("_id", None)
        return txn

    @staticmethod
    async def create_transaction(payload: TransactionCreate) -> Dict[str, Any]:
        coll = db_manager.transactions
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        date_str = now_dt.strftime("%Y-%m-%d")

        # Validate invoice existence if invoice_id is specified
        if payload.invoice_id:
            invoice = await db_manager.invoices.find_one({"id": payload.invoice_id})
            if not invoice:
                # Also check by invoice_number
                invoice = await db_manager.invoices.find_one({"invoice_number": payload.invoice_id})
            if invoice:
                payload.invoice_id = invoice.get("id")
                if not payload.name or payload.name == "Transaction":
                    payload.name = invoice.get("customer_name") or invoice.get("client") or "Invoice Payment"

        # NOTE: Do NOT mark invoice as paid merely because a transaction record exists.
        # Payment confirmation will be handled through PayPal in Phase 3.

        txn_id = generate_id("txn_")
        amount_dec = to_decimal(payload.amount)

        doc = {
            "id": txn_id,
            "invoice_id": payload.invoice_id,
            "paypal_order_id": payload.paypal_order_id,
            "name": payload.name,
            "amount": float(amount_dec),
            "currency": payload.currency.upper(),
            "status": payload.status.value if hasattr(payload.status, "value") else str(payload.status),
            "type": payload.type.value if hasattr(payload.type, "value") else str(payload.type),
            "category": payload.category,
            "payment_method": payload.payment_method.value if hasattr(payload.payment_method, "value") else str(payload.payment_method),
            "date": date_str,
            "created_date": now_iso,
        }

        await coll.insert_one(doc)
        doc.pop("_id", None)
        return doc

