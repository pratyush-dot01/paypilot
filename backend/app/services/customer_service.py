from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.database import db_manager
from app.models.schemas import CustomerCreate, CustomerUpdate
from app.utils.generators import generate_id

class CustomerService:
    @staticmethod
    async def get_customers(limit: int = 50, offset: int = 0, search: Optional[str] = None) -> Dict[str, Any]:
        coll = db_manager.customers
        query = {}
        items = await coll.find(query).skip(offset).limit(limit).to_list(limit)

        # Filter by search string if provided
        if search:
            s_lower = search.lower()
            items = [
                c for c in items
                if s_lower in c.get("name", "").lower()
                or s_lower in c.get("email", "").lower()
                or s_lower in c.get("company", "").lower()
            ]

        total = await coll.count_documents(query)
        # Remove internal MongoDB _id for clean response
        for item in items:
            item.pop("_id", None)

        return {"data": items, "total": total, "limit": limit, "offset": offset}

    @staticmethod
    async def get_customer_by_id(customer_id: str) -> Optional[Dict[str, Any]]:
        coll = db_manager.customers
        customer = await coll.find_one({"id": customer_id})
        if customer:
            customer.pop("_id", None)
        return customer

    @staticmethod
    async def create_customer(payload: CustomerCreate) -> Dict[str, Any]:
        coll = db_manager.customers
        now = datetime.now(timezone.utc).isoformat()
        customer_id = generate_id("cust_")
        doc = {
            "id": customer_id,
            "name": payload.name,
            "email": payload.email,
            "phone": payload.phone,
            "company": payload.company,
            "address": payload.address,
            "created_date": now,
            "updated_date": now,
        }
        await coll.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @staticmethod
    async def update_customer(customer_id: str, payload: CustomerUpdate) -> Optional[Dict[str, Any]]:
        coll = db_manager.customers
        existing = await coll.find_one({"id": customer_id})
        if not existing:
            return None

        update_fields = {}
        for k, v in payload.model_dump(exclude_unset=True).items():
            if v is not None:
                update_fields[k] = v

        if update_fields:
            update_fields["updated_date"] = datetime.now(timezone.utc).isoformat()
            await coll.update_one({"id": customer_id}, {"$set": update_fields})

        updated = await coll.find_one({"id": customer_id})
        if updated:
            updated.pop("_id", None)
        return updated

    @staticmethod
    async def delete_customer(customer_id: str) -> bool:
        coll = db_manager.customers
        existing = await coll.find_one({"id": customer_id})
        if not existing:
            return False
        res = await coll.delete_one({"id": customer_id})
        return res.deleted_count > 0

