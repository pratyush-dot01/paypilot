from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional, List, Dict, Any
from app.models.schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/api/customers", tags=["Customer Management"])

@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate):
    """Create a new customer record."""
    return await CustomerService.create_customer(payload)

@router.get("/")
async def get_customers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    """Retrieve all customers with optional pagination and search filter."""
    return await CustomerService.get_customers(limit=limit, offset=offset, search=search)

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str):
    """Retrieve a specific customer by ID."""
    cust = await CustomerService.get_customer_by_id(customer_id)
    if not cust:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found",
        )
    return cust

@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(customer_id: str, payload: CustomerUpdate):
    """Update an existing customer's contact information."""
    updated = await CustomerService.update_customer(customer_id, payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found",
        )
    return updated

@router.delete("/{customer_id}", status_code=status.HTTP_200_OK)
async def delete_customer(customer_id: str):
    """Delete a customer record."""
    success = await CustomerService.delete_customer(customer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' not found",
        )
    return {"message": "Customer successfully deleted", "id": customer_id}

