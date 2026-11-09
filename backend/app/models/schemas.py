from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum
from decimal import Decimal

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

# -------------------------------------------------------------
# Enums
# -------------------------------------------------------------
class InvoiceStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    paid = "paid"
    overdue = "overdue"

class TransactionStatus(str, Enum):
    completed = "completed"
    pending = "pending"
    failed = "failed"

class TransactionType(str, Enum):
    credit = "credit"
    debit = "debit"

class PaymentMethod(str, Enum):
    paypal = "paypal"
    credit_card = "credit_card"
    bank_transfer = "bank_transfer"
    upi = "upi"
    cash = "cash"
    other = "other"

class ReminderStatus(str, Enum):
    scheduled = "scheduled"
    pending_approval = "pending_approval"
    pending = "pending"
    approved = "approved"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"

# -------------------------------------------------------------
# User Schemas
# -------------------------------------------------------------
class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=EMAIL_PATTERN)

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: str
    created_date: str

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------
# Customer Schemas
# -------------------------------------------------------------
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=150)
    address: Optional[str] = Field(None, max_length=300)

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=150)
    address: Optional[str] = Field(None, max_length=300)

class CustomerResponse(CustomerBase):
    id: str
    created_date: str
    updated_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------
# Invoice Item Schemas
# -------------------------------------------------------------
class InvoiceItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=250)
    quantity: int = Field(1, ge=1)
    unit_price: float = Field(..., ge=0.0)

    @field_validator("quantity")
    def validate_quantity(cls, v):
        if v < 1:
            raise ValueError("Quantity must be at least 1")
        return v

    @field_validator("unit_price")
    def validate_unit_price(cls, v):
        if v < 0:
            raise ValueError("Unit price cannot be negative")
        return v

class InvoiceItemCreate(InvoiceItemBase):
    pass

InvoiceItem = InvoiceItemBase

class InvoiceItemResponse(InvoiceItemBase):
    total: float

# -------------------------------------------------------------
# Invoice Schemas
# -------------------------------------------------------------
class InvoiceBase(BaseModel):
    customer_id: str
    customer_name: Optional[str] = None
    description: str = Field("Invoice", max_length=255)
    items: List[InvoiceItemBase] = Field(..., min_length=1)
    tax_rate: float = Field(18.0, ge=0.0, le=100.0)
    currency: str = Field("INR", max_length=10)
    due_date: str = Field(..., description="Due date in YYYY-MM-DD format")
    status: InvoiceStatus = InvoiceStatus.pending

    @field_validator("items")
    def validate_items_non_empty(cls, v):
        if not v:
            raise ValueError("Invoice must contain at least one item")
        return v

class InvoiceCreate(InvoiceBase):
    invoice_number: Optional[str] = None

class InvoiceUpdate(BaseModel):
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    description: Optional[str] = None
    items: Optional[List[InvoiceItemBase]] = None
    tax_rate: Optional[float] = Field(None, ge=0.0, le=100.0)
    currency: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[InvoiceStatus] = None

class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    # Also provide alias invoice_no for Phase 1 frontend compatibility
    invoice_no: Optional[str] = None
    customer_id: str
    customer_name: Optional[str] = None
    # For Phase 1 frontend compatibility: client alias
    client: Optional[str] = None
    description: str
    items: List[InvoiceItemResponse]
    subtotal: float
    tax_rate: float
    tax: float
    total_amount: float
    # For Phase 1 frontend compatibility: amount alias
    amount: Optional[float] = None
    currency: str
    due_date: str
    status: InvoiceStatus
    created_date: str
    updated_date: Optional[str] = None
    # Phase 3 PayPal integration fields
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    paid_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class InvoiceSummaryResponse(BaseModel):
    total: float
    paid: float
    pending: float
    overdue: float
    draft: float = 0.0
    count: int

# -------------------------------------------------------------
# Transaction Schemas
# -------------------------------------------------------------
class TransactionBase(BaseModel):
    invoice_id: Optional[str] = None
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    payer_email: Optional[str] = None
    payer_name: Optional[str] = None
    name: str = Field("Transaction", max_length=150)
    amount: float = Field(..., ge=0.0)
    currency: str = Field("INR", max_length=10)
    status: TransactionStatus = TransactionStatus.completed
    type: TransactionType = TransactionType.credit
    category: str = Field("General", max_length=100)
    payment_method: PaymentMethod = PaymentMethod.upi

    @field_validator("amount")
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError("Transaction amount cannot be negative")
        return v

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: str
    date: str
    created_date: str

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------
# Reminder Schemas
# -------------------------------------------------------------
class ReminderBase(BaseModel):
    invoice_id: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    message: str = Field(..., min_length=5, max_length=500)
    scheduled_date: str = Field(..., description="Scheduled date in YYYY-MM-DD format")
    status: ReminderStatus = ReminderStatus.scheduled

class ReminderCreate(ReminderBase):
    pass

class ReminderUpdate(BaseModel):
    message: Optional[str] = Field(None, min_length=5, max_length=500)
    scheduled_date: Optional[str] = None
    status: Optional[ReminderStatus] = None

class ReminderResponse(ReminderBase):
    id: str
    created_date: str

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------
# Dashboard & Analytics Schemas
# -------------------------------------------------------------
class DashboardStats(BaseModel):
    total_revenue: float
    pending_payments: float
    completed_transactions: int
    overdue_invoices: int

class RevenueChartItem(BaseModel):
    month: str
    revenue: float
    expenses: float

class RevenueChartResponse(BaseModel):
    data: List[RevenueChartItem]

# -------------------------------------------------------------
# AI Chat Schemas (Phase 1/2)
# -------------------------------------------------------------
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str

# -------------------------------------------------------------
# Health Check Schema
# -------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    collections: Optional[dict] = None

# -------------------------------------------------------------
# Phase 3 PayPal Payment Schemas
# -------------------------------------------------------------
class PayPalPaymentStatus(str, Enum):
    created = "CREATED"
    approved = "APPROVED"
    pending = "PENDING"
    completed = "COMPLETED"
    failed = "FAILED"
    cancelled = "CANCELLED"

class CreateOrderRequest(BaseModel):
    invoice_id: str = Field(..., description="The ID or invoice number of the invoice to pay")

class CreateOrderResponse(BaseModel):
    order_id: str
    approval_url: Optional[str] = None
    invoice_id: str
    invoice_number: str
    amount: float
    currency: str
    status: str
    mode: str

class CaptureOrderRequest(BaseModel):
    order_id: str = Field(..., description="PayPal Order ID approved by customer")
    invoice_id: Optional[str] = Field(None, description="Associated invoice ID for validation")

class CaptureOrderResponse(BaseModel):
    status: str
    message: str
    transaction_id: str
    invoice_id: str
    invoice_number: str
    paypal_order_id: str
    paypal_capture_id: str
    amount: float
    currency: str
    payer_email: Optional[str] = None
    payer_name: Optional[str] = None

class PayPalConfigResponse(BaseModel):
    client_id: str
    currency: str
    mode: str
    is_live: bool

class WebhookResponse(BaseModel):
    status: str
    event_type: str
    event_id: str
    message: str

# -------------------------------------------------------------
# Phase 4: AI Agent Schemas
# -------------------------------------------------------------
class IntentType(str, Enum):
    CREATE_INVOICE = "CREATE_INVOICE"
    VIEW_INVOICES = "VIEW_INVOICES"
    VIEW_TRANSACTIONS = "VIEW_TRANSACTIONS"
    CHECK_PENDING_PAYMENTS = "CHECK_PENDING_PAYMENTS"
    CHECK_OVERDUE_INVOICES = "CHECK_OVERDUE_INVOICES"
    ANALYZE_REVENUE = "ANALYZE_REVENUE"
    GENERATE_REMINDER = "GENERATE_REMINDER"
    PAYMENT_STATUS = "PAYMENT_STATUS"
    GENERAL_FINANCIAL_QUERY = "GENERAL_FINANCIAL_QUERY"

class ExtractedEntities(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "INR"
    description: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    due_date: Optional[str] = None
    invoice_id: Optional[str] = None
    transaction_id: Optional[str] = None
    date_range: Optional[str] = None

class ToolCallResult(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None

class ActionConfirmation(BaseModel):
    action: str
    description: str
    parameters: Dict[str, Any] = {}
    requires_confirmation: bool = True

class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's natural language input")
    conversation_id: Optional[str] = Field(None, description="Unique conversation session ID")
    confirmed_action: Optional[Dict[str, Any]] = Field(None, description="Explicit action payload confirmed by user")

class AIChatResponse(BaseModel):
    conversation_id: str
    response: str
    intent: str
    entities: ExtractedEntities
    missing_entities: List[str] = []
    clarification_needed: bool = False
    tools_executed: List[ToolCallResult] = []
    confirmation_required: Optional[ActionConfirmation] = None
    action_completed: Optional[Dict[str, Any]] = None
    data_preview: Optional[Dict[str, Any]] = None
    timestamp: str
    model_used: str
    grounded: bool = True

class ConversationTurn(BaseModel):
    turn_id: str
    role: str  # 'user' or 'assistant'
    message: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    timestamp: str

class ConversationSummary(BaseModel):
    conversation_id: str
    turn_count: int
    last_message: str
    last_intent: Optional[str] = None
    created_at: str
    updated_at: str

class ConversationDetail(BaseModel):
    conversation_id: str
    created_at: str
    updated_at: str
    turns: List[ConversationTurn] = []

class AIStatusResponse(BaseModel):
    status: str
    provider: str
    model: str
    api_key_configured: bool
    live_connectivity: bool
    latency_ms: Optional[float] = None
    supported_intents: List[str]

# -------------------------------------------------------------
# Phase 6: Notifications Schemas
# -------------------------------------------------------------
class NotificationType(str, Enum):
    reminder = "reminder"
    anomaly = "anomaly"
    invoice_deadline = "invoice_deadline"
    overdue_alert = "overdue_alert"
    system = "system"

class NotificationChannel(str, Enum):
    in_app = "in_app"
    email = "email"

class NotificationDeliveryStatus(str, Enum):
    unread = "unread"
    read = "read"
    sent = "sent"
    failed = "failed"
    simulated = "simulated"
    unconfigured = "unconfigured"

class NotificationCreate(BaseModel):
    type: NotificationType
    channel: NotificationChannel = NotificationChannel.in_app
    title: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=2, max_length=2000)
    recipient_email: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class NotificationResponse(BaseModel):
    id: str
    type: str
    channel: str
    title: str
    message: str
    recipient_email: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    delivery_status: str
    delivery_details: Optional[Dict[str, Any]] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------
# Phase 6: Financial Intelligence & Anomaly Schemas
# -------------------------------------------------------------
class MonthOverMonthComparison(BaseModel):
    current_month: str
    previous_month: str
    current_month_revenue: float
    previous_month_revenue: float
    growth_rate_pct: float
    trend_direction: str  # "up", "down", "flat"
    explanation: str

class RevenueForecast(BaseModel):
    target_period: str
    forecast_amount: float
    forecast_method: str
    confidence_level: str  # "high", "medium", "low"
    is_estimated: bool = True
    disclaimer: str = "Forecast is an algorithmic estimate based on historical database revenue; actual results may vary."
    historical_basis_revenue: float

class CustomerPaymentBehavior(BaseModel):
    customer_id: str
    customer_name: str
    company: Optional[str] = None
    total_invoices: int
    paid_count: int
    overdue_count: int
    pending_count: int
    total_billed: float
    total_paid: float
    outstanding_balance: float
    late_payment_ratio_pct: float
    risk_level: str  # "low", "medium", "high"

class FinancialIntelligenceResponse(BaseModel):
    daily_revenue: float
    weekly_revenue: float
    monthly_revenue: float
    outstanding_amount: float
    overdue_amount: float
    mom_comparison: MonthOverMonthComparison
    forecast: RevenueForecast
    top_customer_breakdown: List[CustomerPaymentBehavior]
    transaction_trend: str
    generated_at: str

class AnomalyType(str, Enum):
    unusually_large_transaction = "unusually_large_transaction"
    sudden_revenue_drop = "sudden_revenue_drop"
    repeated_failed_payments = "repeated_failed_payments"
    frequent_late_payer = "frequent_late_payer"
    unusual_payment_pattern = "unusual_payment_pattern"

class AnomalySeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class FinancialAnomaly(BaseModel):
    anomaly_id: str
    type: AnomalyType
    severity: AnomalySeverity
    title: str
    description: str
    explanation: str
    metrics: Dict[str, Any] = {}
    advisory_only: bool = True
    detected_at: str

class AnomalyDetectionResponse(BaseModel):
    anomalies_detected: int
    anomalies: List[FinancialAnomaly]
    summary: str
    generated_at: str

# -------------------------------------------------------------
# Phase 6: Automation & Scheduler Schemas
# -------------------------------------------------------------
class AutomationJobInfo(BaseModel):
    id: str
    name: str
    trigger: str
    next_run_time: Optional[str] = None
    is_active: bool = True
    description: str

class AutomationLog(BaseModel):
    id: str
    job_id: str
    job_name: str
    status: str  # "success", "failed", "warning"
    summary: str
    details: Optional[Dict[str, Any]] = None
    executed_at: str
    duration_ms: float

class AutomationStatusResponse(BaseModel):
    scheduler_running: bool
    timezone: str
    jobs: List[AutomationJobInfo]
    recent_logs: List[AutomationLog]
    total_jobs: int

class ReminderApprovalRequest(BaseModel):
    reminder_id: str
    approved: bool = True
    channel: NotificationChannel = NotificationChannel.in_app
    custom_message: Optional[str] = None

class BatchReminderGenerateRequest(BaseModel):
    days_ahead: int = 3
    overdue_only: bool = False
    tone: str = "professional"



