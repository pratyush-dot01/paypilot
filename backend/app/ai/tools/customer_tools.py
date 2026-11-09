"""
Customer Tools for PayPilot AI Agent (Phase 5).
Interacts directly with CustomerService for customer lookup, creation, and profile retrieval.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.ai.tools.base import BaseTool
from app.services.customer_service import CustomerService
from app.models.schemas import CustomerCreate

class CreateCustomerInput(BaseModel):
    name: str = Field(..., description="Customer full name or contact person")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer contact phone number")
    company: Optional[str] = Field(None, description="Company or business name")

class CreateCustomerTool(BaseTool):
    name = "create_customer"
    description = "Create a new customer profile in the PayPilot database."
    input_schema = CreateCustomerInput

    async def run(
        self,
        name: str,
        email: str,
        phone: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = CustomerCreate(
            name=name,
            email=email,
            phone=phone,
            company=company or name,
        )
        created = await CustomerService.create_customer(payload)
        return {
            "customer_id": created["id"],
            "name": created["name"],
            "email": created["email"],
            "company": created.get("company"),
        }

class SearchCustomerInput(BaseModel):
    query: str = Field(..., description="Customer name, company, or email keyword to search for")

class SearchCustomerTool(BaseTool):
    name = "search_customer"
    description = "Search for an existing customer in the database by name, company, or email."
    input_schema = SearchCustomerInput

    async def run(self, query: str) -> Dict[str, Any]:
        res = await CustomerService.get_customers(search=query, limit=5)
        customers = res.get("data", [])
        return {
            "found": len(customers) > 0,
            "count": len(customers),
            "customers": [
                {
                    "customer_id": c["id"],
                    "name": c.get("name"),
                    "email": c.get("email"),
                    "company": c.get("company"),
                }
                for c in customers
            ],
        }

class GetCustomerDetailsInput(BaseModel):
    customer_id: str = Field(..., description="Unique customer ID (e.g. cust_...)")

class GetCustomerDetailsTool(BaseTool):
    name = "get_customer_details"
    description = "Retrieve full customer profile details by customer ID."
    input_schema = GetCustomerDetailsInput

    async def run(self, customer_id: str) -> Dict[str, Any]:
        customer = await CustomerService.get_customer_by_id(customer_id)
        if not customer:
            return {"found": False, "message": f"Customer '{customer_id}' not found"}
        return {
            "found": True,
            "customer_id": customer["id"],
            "name": customer.get("name"),
            "email": customer.get("email"),
            "phone": customer.get("phone"),
            "company": customer.get("company"),
        }

