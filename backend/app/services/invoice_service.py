from datetime import datetime, date, timezone
from typing import List, Optional, Dict, Any
from decimal import Decimal
from app.database import db_manager
from app.models.schemas import InvoiceCreate, InvoiceUpdate, InvoiceStatus
from app.utils.calculations import calculate_invoice_totals, calculate_item_total, to_decimal
from app.utils.generators import generate_id, generate_invoice_number

class InvoiceService:
    @staticmethod
    def _is_overdue(due_date_str: str, current_status: str) -> bool:
        """Check if an invoice has passed its due date and should be overdue."""
        if current_status not in ["pending", "draft"]:
            return False
        try:
            due_d = datetime.strptime(due_date_str.split("T")[0], "%Y-%m-%d").date()
            return due_d < date.today()
        except Exception:
            return False

    @classmethod
    async def _check_and_update_overdue(cls, invoice_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically detect overdue condition and persist if needed."""
        status = invoice_doc.get("status")
        due_date = invoice_doc.get("due_date", "")
        if cls._is_overdue(due_date, status):
            invoice_doc["status"] = InvoiceStatus.overdue.value
            await db_manager.invoices.update_one(
                {"id": invoice_doc["id"]},
                {"$set": {"status": InvoiceStatus.overdue.value, "updated_date": datetime.now(timezone.utc).isoformat()}}
            )
        # Add frontend backward compatibility aliases
        invoice_doc["invoice_no"] = invoice_doc.get("invoice_number")
        invoice_doc["client"] = invoice_doc.get("customer_name")
        invoice_doc["amount"] = invoice_doc.get("total_amount")
        invoice_doc.pop("_id", None)
        return invoice_doc

    @classmethod
    async def get_invoices(
        cls,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        coll = db_manager.invoices
        query = {}
        if customer_id:
            query["customer_id"] = customer_id

        # First retrieve candidates
        raw_items = await coll.find(query).skip(offset).limit(limit).to_list(limit)

        # Check and update overdue statuses
        processed = []
        for doc in raw_items:
            updated_doc = await cls._check_and_update_overdue(doc)
            # Filter by status after overdue detection
            if status and updated_doc.get("status") != status:
                continue
            if search:
                s_lower = search.lower()
                inv_no = updated_doc.get("invoice_number", "").lower()
                client_name = (updated_doc.get("customer_name") or "").lower()
                desc = updated_doc.get("description", "").lower()
                if not (s_lower in inv_no or s_lower in client_name or s_lower in desc):
                    continue
            processed.append(updated_doc)

        total = await coll.count_documents(query)
        return {"data": processed, "total": total, "limit": limit, "offset": offset}

    @classmethod
    async def get_invoice_by_id(cls, invoice_id: str) -> Optional[Dict[str, Any]]:
        coll = db_manager.invoices
        doc = await coll.find_one({"id": invoice_id})
        if not doc:
            # Also search by invoice_number
            doc = await coll.find_one({"invoice_number": invoice_id})
        if not doc:
            return None
        return await cls._check_and_update_overdue(doc)

    @classmethod
    async def create_invoice(cls, payload: InvoiceCreate) -> Dict[str, Any]:
        coll = db_manager.invoices
        now = datetime.now(timezone.utc).isoformat()
        invoice_id = generate_id("inv_")

        # 1. Automatic invoice number generation
        if not payload.invoice_number:
            count = await coll.count_documents({})
            seq = count + 1
            invoice_number = generate_invoice_number(sequence=seq, year=datetime.now().year)
            # Ensure uniqueness
            while await coll.find_one({"invoice_number": invoice_number}):
                seq += 1
                invoice_number = generate_invoice_number(sequence=seq, year=datetime.now().year)
        else:
            invoice_number = payload.invoice_number

        # 2. Look up customer name if not provided
        customer_name = payload.customer_name
        if not customer_name and payload.customer_id:
            customer = await db_manager.customers.find_one({"id": payload.customer_id})
            if customer:
                customer_name = customer.get("name")
        if not customer_name:
            customer_name = "Valued Customer"

        # 3. Monetary calculations using Decimal
        items_data = []
        for item in payload.items:
            item_dict = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            qty = item_dict.get("quantity", 1)
            u_price = item_dict.get("unit_price", 0.0)
            item_total = calculate_item_total(qty, u_price)
            item_dict["total"] = float(item_total)
            items_data.append(item_dict)

        subtotal, tax_amount, total_amount = calculate_invoice_totals(items_data, payload.tax_rate)

        # 4. Check initial overdue condition
        status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
        if cls._is_overdue(payload.due_date, status):
            status = InvoiceStatus.overdue.value

        doc = {
            "id": invoice_id,
            "invoice_number": invoice_number,
            "invoice_no": invoice_number,
            "customer_id": payload.customer_id,
            "customer_name": customer_name,
            "client": customer_name,
            "description": payload.description,
            "items": items_data,
            "subtotal": float(subtotal),
            "tax_rate": float(payload.tax_rate),
            "tax": float(tax_amount),
            "total_amount": float(total_amount),
            "amount": float(total_amount),
            "currency": payload.currency.upper(),
            "due_date": payload.due_date,
            "status": status,
            "created_date": now,
            "updated_date": now,
        }

        await coll.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @classmethod
    async def update_invoice(cls, invoice_id: str, payload: InvoiceUpdate) -> Optional[Dict[str, Any]]:
        coll = db_manager.invoices
        existing = await coll.find_one({"id": invoice_id})
        if not existing:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            existing.pop("_id", None)
            return existing

        # If items or tax_rate changed, recalculate using Decimal
        if "items" in update_data or "tax_rate" in update_data:
            items_to_calc = update_data.get("items", existing.get("items", []))
            tax_rate_to_calc = update_data.get("tax_rate", existing.get("tax_rate", 18.0))

            items_data = []
            for item in items_to_calc:
                item_dict = item if isinstance(item, dict) else (item.model_dump() if hasattr(item, "model_dump") else dict(item))
                qty = item_dict.get("quantity", 1)
                u_price = item_dict.get("unit_price", 0.0)
                item_total = calculate_item_total(qty, u_price)
                item_dict["total"] = float(item_total)
                items_data.append(item_dict)

            subtotal, tax_amount, total_amount = calculate_invoice_totals(items_data, tax_rate_to_calc)
            update_data["items"] = items_data
            update_data["subtotal"] = float(subtotal)
            update_data["tax"] = float(tax_amount)
            update_data["total_amount"] = float(total_amount)
            update_data["amount"] = float(total_amount)

        # Overdue check on due date update
        due_date = update_data.get("due_date", existing.get("due_date", ""))
        current_status = update_data.get("status", existing.get("status", "pending"))
        if hasattr(current_status, "value"):
            current_status = current_status.value
        if cls._is_overdue(due_date, current_status):
            update_data["status"] = InvoiceStatus.overdue.value

        update_data["updated_date"] = datetime.now(timezone.utc).isoformat()
        await coll.update_one({"id": invoice_id}, {"$set": update_data})

        updated = await coll.find_one({"id": invoice_id})
        return await cls._check_and_update_overdue(updated)

    @staticmethod
    async def delete_invoice(invoice_id: str) -> bool:
        coll = db_manager.invoices
        existing = await coll.find_one({"id": invoice_id})
        if not existing:
            return False
        res = await coll.delete_one({"id": invoice_id})
        return res.deleted_count > 0

    @classmethod
    async def get_summary(cls) -> Dict[str, Any]:
        """Calculate invoice summary statistics using Decimal arithmetic."""
        coll = db_manager.invoices
        invoices = await coll.find({}).to_list(1000)

        total_dec = Decimal("0.00")
        paid_dec = Decimal("0.00")
        pending_dec = Decimal("0.00")
        overdue_dec = Decimal("0.00")
        draft_dec = Decimal("0.00")

        for inv in invoices:
            updated_inv = await cls._check_and_update_overdue(inv)
            amt = to_decimal(updated_inv.get("total_amount", 0.0))
            st = updated_inv.get("status")
            total_dec += amt
            if st == "paid":
                paid_dec += amt
            elif st == "pending":
                pending_dec += amt
            elif st == "overdue":
                overdue_dec += amt
            elif st == "draft":
                draft_dec += amt

        return {
            "total": float(total_dec),
            "paid": float(paid_dec),
            "pending": float(pending_dec),
            "overdue": float(overdue_dec),
            "draft": float(draft_dec),
            "count": len(invoices),
        }

