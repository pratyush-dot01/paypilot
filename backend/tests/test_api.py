import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from app.main import app
from app.database import connect_to_mongo
from app.utils.calculations import calculate_invoice_totals, calculate_item_total, to_decimal
from decimal import Decimal

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await connect_to_mongo()

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"
        assert "database" in data
        assert "collections" in data

@pytest.mark.asyncio
async def test_decimal_calculations():
    # Test item calculations
    item_tot = calculate_item_total(3, "150.50")
    assert item_tot == Decimal("451.50")

    # Test invoice totals with tax
    items = [
        {"quantity": 2, "unit_price": 500.00},  # 1000.00
        {"quantity": 1, "unit_price": 250.50},  # 250.50
    ]
    # subtotal = 1250.50, tax 18% = 225.09, total = 1475.59
    subtotal, tax, total = calculate_invoice_totals(items, 18.0)
    assert subtotal == Decimal("1250.50")
    assert tax == Decimal("225.09")
    assert total == Decimal("1475.59")

@pytest.mark.asyncio
async def test_customer_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create customer
        create_res = await client.post("/api/customers/", json={
            "name": "Acme Innovations",
            "email": "billing@acme.example.com",
            "phone": "+91 99999 88888",
            "company": "Acme Corp Ltd",
            "address": "Electronic City, Bengaluru",
        })
        assert create_res.status_code == 201
        customer = create_res.json()
        assert customer["name"] == "Acme Innovations"
        cust_id = customer["id"]

        # 2. Get customer by ID
        get_res = await client.get(f"/api/customers/{cust_id}")
        assert get_res.status_code == 200
        assert get_res.json()["email"] == "billing@acme.example.com"

        # 3. Update customer
        update_res = await client.put(f"/api/customers/{cust_id}", json={
            "company": "Acme Global Corp",
        })
        assert update_res.status_code == 200
        assert update_res.json()["company"] == "Acme Global Corp"

        # 4. List customers
        list_res = await client.get("/api/customers/")
        assert list_res.status_code == 200
        assert any(c["id"] == cust_id for c in list_res.json()["data"])

        # 5. Delete customer
        del_res = await client.delete(f"/api/customers/{cust_id}")
        assert del_res.status_code == 200

        # Verify 404 after delete
        not_found = await client.get(f"/api/customers/{cust_id}")
        assert not_found.status_code == 404

@pytest.mark.asyncio
async def test_invoice_creation_calculations_and_overdue_detection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create standard pending invoice
        future_date = (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d")
        create_res = await client.post("/api/invoices/", json={
            "customer_id": "cust_001",
            "customer_name": "TechCorp Solutions",
            "description": "Full Stack Engineering Services",
            "items": [
                {"description": "Backend API Development", "quantity": 2, "unit_price": 25000.0},
                {"description": "Database Optimization", "quantity": 1, "unit_price": 10000.0},
            ],
            "tax_rate": 18.0,
            "currency": "INR",
            "due_date": future_date,
            "status": "pending",
        })
        assert create_res.status_code == 201
        inv = create_res.json()
        assert inv["invoice_number"].startswith("INV-")
        assert inv["subtotal"] == 60000.0
        assert inv["tax"] == 10800.0
        assert inv["total_amount"] == 70800.0
        assert inv["status"] == "pending"
        inv_id = inv["id"]

        # 2. Create invoice with PAST due date -> Automatic Overdue Detection
        past_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        past_res = await client.post("/api/invoices/", json={
            "customer_id": "cust_001",
            "customer_name": "TechCorp Solutions",
            "description": "Legacy Audit Service",
            "items": [
                {"description": "System Audit", "quantity": 1, "unit_price": 15000.0},
            ],
            "tax_rate": 18.0,
            "currency": "INR",
            "due_date": past_date,
            "status": "pending",
        })
        assert past_res.status_code == 201
        past_inv = past_res.json()
        assert past_inv["status"] == "overdue", "Past due date must be automatically detected as overdue"

        # 3. Get invoice summary
        sum_res = await client.get("/api/invoices/summary")
        assert sum_res.status_code == 200
        summary = sum_res.json()
        assert summary["total"] > 0
        assert summary["overdue"] > 0

@pytest.mark.asyncio
async def test_transaction_association_without_auto_marking_paid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a transaction linked to inv_001
        txn_res = await client.post("/api/transactions/", json={
            "invoice_id": "inv_001",
            "name": "TechCorp Partial Payment",
            "amount": 25000.0,
            "currency": "INR",
            "status": "completed",
            "type": "credit",
            "category": "Invoice Payment",
            "payment_method": "bank_transfer",
        })
        assert txn_res.status_code == 201
        txn = txn_res.json()
        assert txn["invoice_id"] == "inv_001"
        assert txn["amount"] == 25000.0

        # Important business rule verification:
        # Verify invoice is NOT automatically marked as paid merely because transaction exists
        inv_res = await client.get("/api/invoices/inv_001")
        assert inv_res.status_code == 200
        inv = inv_res.json()
        assert inv["status"] != "paid", "Invoice must NOT be automatically marked paid (reserved for Phase 3 PayPal confirmation)"

@pytest.mark.asyncio
async def test_reminder_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create reminder
        create_res = await client.post("/api/reminders/", json={
            "invoice_id": "inv_001",
            "message": "Gentle reminder regarding pending payment for INV-2026-0001",
            "scheduled_date": "2026-11-18",
            "status": "scheduled",
        })
        assert create_res.status_code == 201
        rem = create_res.json()
        assert rem["invoice_id"] == "inv_001"
        rem_id = rem["id"]

        # 2. Update status
        patch_res = await client.patch(f"/api/reminders/{rem_id}/status?status=sent")
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "sent"

        # 3. List reminders
        list_res = await client.get(f"/api/reminders/?invoice_id=inv_001")
        assert list_res.status_code == 200
        assert any(r["id"] == rem_id for r in list_res.json()["data"])

@pytest.mark.asyncio
async def test_dashboard_analytics():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        stats_res = await client.get("/api/dashboard/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_revenue"] > 0
        assert stats["pending_payments"] > 0
        assert stats["completed_transactions"] > 0
        assert stats["overdue_invoices"] >= 1

        chart_res = await client.get("/api/dashboard/revenue-chart")
        assert chart_res.status_code == 200
        chart_data = chart_res.json()["data"]
        assert len(chart_data) == 12

        recent_res = await client.get("/api/dashboard/recent-transactions")
        assert recent_res.status_code == 200
        assert len(recent_res.json()["data"]) > 0

@pytest.mark.asyncio
async def test_ai_assistant_chat():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        chat_res = await client.post("/api/chat/", json={"message": "Show my pending payments"})
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "response" in chat_data
        assert "pending" in chat_data["response"].lower() or "₹" in chat_data["response"]

@pytest.mark.asyncio
async def test_paypal_payment_flow_and_idempotency():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Test public PayPal config endpoint
        cfg_res = await client.get("/api/payments/config")
        assert cfg_res.status_code == 200
        cfg = cfg_res.json()
        assert "client_id" in cfg
        assert cfg["mode"] == "sandbox"
        assert cfg["is_live"] is False
        assert "client_secret" not in cfg

        # 2. Create invoice for payment test
        inv_res = await client.post("/api/invoices/", json={
            "customer_id": "cust_001",
            "customer_name": "Acme Global Solutions",
            "description": "PayPal Sandbox Payment Verification",
            "items": [
                {"description": "Production License", "quantity": 1, "unit_price": 500.0},
            ],
            "tax_rate": 0.0,
            "currency": "USD",
            "due_date": "2026-12-31",
            "status": "pending",
        })
        assert inv_res.status_code == 201
        test_inv = inv_res.json()
        inv_id = test_inv["id"]

        # 3. Create PayPal Order
        order_res = await client.post("/api/payments/create-order", json={"invoice_id": inv_id})
        assert order_res.status_code == 201
        order = order_res.json()
        assert "order_id" in order
        assert order["invoice_id"] == inv_id
        assert order["status"] in ["CREATED", "SAVED"]
        real_or_test_order_id = order["order_id"]

        # 4. Capture PayPal Order (simulate approval with TEST_ order ID)
        test_order_id = f"TEST_{real_or_test_order_id}"
        # Associate test_order_id with the invoice
        from app.database import db_manager
        await db_manager.invoices.update_one({"id": inv_id}, {"$set": {"paypal_order_id": test_order_id}})

        cap_res = await client.post("/api/payments/capture-order", json={
            "order_id": test_order_id,
            "invoice_id": inv_id,
        })
        assert cap_res.status_code == 200
        cap_data = cap_res.json()
        assert cap_data["status"] == "COMPLETED"
        assert cap_data["paypal_order_id"] == test_order_id
        assert "transaction_id" in cap_data

        # 5. Verify invoice status updated to 'paid' in MongoDB
        inv_check = await client.get(f"/api/invoices/{inv_id}")
        assert inv_check.status_code == 200
        assert inv_check.json()["status"] == "paid"
        assert inv_check.json()["paypal_capture_id"] is not None

        # 6. Idempotency Check: Capturing the same order again should NOT duplicate
        cap_dup = await client.post("/api/payments/capture-order", json={
            "order_id": test_order_id,
            "invoice_id": inv_id,
        })
        assert cap_dup.status_code == 200
        assert cap_dup.json()["status"] == "COMPLETED"
        assert cap_dup.json()["transaction_id"] == cap_data["transaction_id"]

        # 7. Reject creating order for already paid invoice
        paid_res = await client.post("/api/payments/create-order", json={"invoice_id": inv_id})
        assert paid_res.status_code == 400
        assert "already paid" in paid_res.json()["detail"].lower()

        # 8. Test invoice payment details endpoint
        pay_info = await client.get(f"/api/payments/invoice/{inv_id}")
        assert pay_info.status_code == 200
        assert pay_info.json()["is_paid"] is True
        assert len(pay_info.json()["transactions"]) >= 1

@pytest.mark.asyncio
async def test_paypal_webhooks():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create invoice to test webhook capture
        inv_res = await client.post("/api/invoices/", json={
            "customer_id": "cust_002",
            "customer_name": "Webhook Test Co",
            "description": "Webhook Test Service",
            "items": [{"description": "Service", "quantity": 1, "unit_price": 200.0}],
            "tax_rate": 0.0,
            "currency": "USD",
            "due_date": "2026-12-31",
            "status": "pending",
        })
        test_inv = inv_res.json()
        inv_id = test_inv["id"]

        # 1. Invalid webhook headers should be rejected
        bad_res = await client.post("/api/payments/webhook", json={"event_type": "TEST"})
        assert bad_res.status_code == 400

        # 2. Valid webhook transmission headers
        headers = {
            "paypal-transmission-id": "trans_test_001",
            "paypal-transmission-sig": "test_sig_001",
            "paypal-transmission-time": "2026-11-09T15:00:00Z",
            "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-360",
            "paypal-auth-algo": "SHA256withRSA",
        }
        import uuid
        unique_event_id = f"WH-TEST-{uuid.uuid4().hex[:8]}"
        event_payload = {
            "id": unique_event_id,
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": f"CAP-{unique_event_id}",
                "custom_id": inv_id,
                "amount": {"value": "200.00", "currency_code": "USD"},
            },
            "summary": "Payment capture completed",
        }

        wh_res = await client.post("/api/payments/webhook", json=event_payload, headers=headers)
        assert wh_res.status_code == 200
        assert wh_res.json()["status"] == "success"

        # Check invoice transitioned to paid by webhook
        inv_check = await client.get(f"/api/invoices/{inv_id}")
        assert inv_check.json()["status"] == "paid"

        # 3. Webhook idempotency: Re-delivery of same event
        wh_dup = await client.post("/api/payments/webhook", json=event_payload, headers=headers)
        assert wh_dup.status_code == 200
        assert wh_dup.json()["status"] == "duplicate"

@pytest.mark.asyncio
async def test_ai_status_and_prompts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        status_res = await client.get("/api/ai/status")
        assert status_res.status_code == 200
        data = status_res.json()
        assert "provider" in data
        assert "model" in data
        assert len(data["supported_intents"]) == 9

        prompts_res = await client.get("/api/ai/suggested-prompts")
        assert prompts_res.status_code == 200
        prompts = prompts_res.json()
        assert isinstance(prompts, list)
        assert len(prompts) >= 3

@pytest.mark.asyncio
async def test_ai_intent_and_entity_extraction():
    from app.ai.intent_classifier import IntentClassifier
    from app.ai.entity_extractor import EntityExtractor

    # 1. Test intents
    intents = [
        ("Create invoice for ₹5,000 to TechCorp", "CREATE_INVOICE"),
        ("Show my pending payments", "CHECK_PENDING_PAYMENTS"),
        ("Which invoices are overdue?", "CHECK_OVERDUE_INVOICES"),
        ("Analyse my monthly revenue", "ANALYZE_REVENUE"),
        ("Show my latest five transactions", "VIEW_TRANSACTIONS"),
        ("Send reminder for overdue invoice", "GENERATE_REMINDER"),
        ("What is status of invoice INV-2026-0001?", "PAYMENT_STATUS"),
        ("List all invoices", "VIEW_INVOICES"),
        ("General financial query", "GENERAL_FINANCIAL_QUERY"),
    ]
    for text, expected in intents:
        classified, _ = IntentClassifier.classify(text)
        assert classified == expected, f"Failed for {text}: expected {expected}, got {classified}"

    # 2. Test entity extraction
    extracted = EntityExtractor.extract_all("Create an invoice for ₹25,000 to Startup Labs due tomorrow")
    assert extracted["amount"] == 25000.0
    assert extracted["customer_name"] == "Startup Labs"
    assert extracted["currency"] == "INR"
    assert extracted["due_date"] is not None

@pytest.mark.asyncio
async def test_ai_grounded_multiturn_chat():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First turn
        res1 = await client.post("/api/ai/chat", json={"message": "Show my pending payments"})
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["intent"] == "CHECK_PENDING_PAYMENTS"
        conv_id = data1["conversation_id"]

        # Follow up in same conversation
        res2 = await client.post("/api/ai/chat", json={
            "message": "Which one has the highest amount?",
            "conversation_id": conv_id,
        })
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["conversation_id"] == conv_id

        # Verify turns recorded
        conv_res = await client.get(f"/api/ai/conversations/{conv_id}")
        assert conv_res.status_code == 200
        assert len(conv_res.json()["turns"]) >= 2

        # Cleanup
        del_res = await client.delete(f"/api/ai/conversations/{conv_id}")
        assert del_res.status_code == 200

@pytest.mark.asyncio
async def test_ai_tool_calling_invoice_and_clarification():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Clarification needed
        res1 = await client.post("/api/ai/chat", json={"message": "Create an invoice please"})
        assert res1.status_code == 200
        assert res1.json()["clarification_needed"] is True

        # 2. Complete invoice creation
        res2 = await client.post("/api/ai/chat", json={
            "message": "Create an invoice for ₹8,000 for BetaCorp due in 10 days"
        })
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2["tools_executed"]) >= 1
        tool = data2["tools_executed"][0]
        assert tool["tool_name"] == "create_invoice"
        assert tool["success"] is True
        assert tool["result"]["total_amount"] == 9440.0  # 8000 + 18% GST

@pytest.mark.asyncio
async def test_ai_tool_calling_user_confirmation_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create an invoice first for isolation
        inv_res = await client.post("/api/invoices/", json={
            "customer_id": "cust_001",
            "customer_name": "BetaCorp",
            "description": "Consulting Services",
            "items": [{"description": "Work", "quantity": 1, "unit_price": 5000.0}],
            "currency": "USD",
            "due_date": "2026-12-31",
            "status": "pending",
        })
        inv_id = inv_res.json()["id"]

        conv_id = "conv_test_confirm_flow"
        # 1. User asks for payment link
        res1 = await client.post("/api/ai/chat", json={
            "message": f"Create a payment link for invoice {inv_id}",
            "conversation_id": conv_id,
        })
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["confirmation_required"] is not None
        assert data1["confirmation_required"]["action"] == "create_paypal_order"

        # 2. User confirms
        res2 = await client.post("/api/ai/chat", json={
            "message": "Yes, generate it.",
            "conversation_id": conv_id,
        })
        assert res2.status_code == 200
        data2 = res2.json()
        assert any(t["tool_name"] == "create_paypal_order" for t in data2["tools_executed"])
        assert data2["action_completed"] is not None

@pytest.mark.asyncio
async def test_ai_tool_registry_and_validation():
    from app.ai.tools.registry import ToolRegistry
    # Validation check: negative amount must fail
    res = await ToolRegistry.execute_tool("create_invoice", {"amount": -100})
    assert res["success"] is False
    assert res["error"] is not None

    # Unregistered tool
    fake = await ToolRegistry.execute_tool("unauthorized_tool", {})
    assert fake["success"] is False

# =============================================================
# Phase 6: Automated Tasks, Financial Intelligence & Anomalies
# =============================================================

@pytest.mark.asyncio
async def test_overdue_and_upcoming_invoice_detection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Overdue check
        res = await client.get("/api/reminders/overdue-invoices")
        assert res.status_code == 200
        assert "data" in res.json()

        # Upcoming due-date check
        res_up = await client.get("/api/reminders/upcoming-invoices?days_ahead=3")
        assert res_up.status_code == 200
        assert "data" in res_up.json()

@pytest.mark.asyncio
async def test_reminder_generation_and_deduplication():
    from app.services.reminder_service import ReminderService
    from app.models.schemas import ReminderCreate
    # Generation
    sample = {
        "invoice_number": "INV-2026-0999",
        "customer_name": "Test Client",
        "total_amount": 50000.0,
        "due_date": "2026-11-01",
        "status": "overdue",
        "days_overdue": 5,
    }
    msg = ReminderService.generate_personalized_message(sample, tone="professional")
    assert "Test Client" in msg
    assert "INV-2026-0999" in msg

    # Deduplication
    inv_id = "inv_test_dedup_pytest"
    r1 = await ReminderService.create_reminder(ReminderCreate(
        invoice_id=inv_id,
        message="Notice 1",
        scheduled_date="2026-11-10",
    ))
    r2 = await ReminderService.create_reminder(ReminderCreate(
        invoice_id=inv_id,
        message="Notice 2",
        scheduled_date="2026-11-10",
    ))
    assert r2.get("duplicate_prevented") is True
    assert r2["id"] == r1["id"]

@pytest.mark.asyncio
async def test_reminder_approval_workflow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        from app.services.reminder_service import ReminderService
        from app.models.schemas import ReminderCreate, ReminderStatus
        rem = await ReminderService.create_reminder(ReminderCreate(
            invoice_id="inv_pytest_approval",
            message="Please pay invoice",
            scheduled_date="2026-11-10",
            status=ReminderStatus.pending_approval,
        ))
        rem_id = rem["id"]
        res = await client.post(f"/api/reminders/{rem_id}/approve", json={"reminder_id": rem_id})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["status"] == "sent"

@pytest.mark.asyncio
async def test_scheduled_task_execution_and_logging():
    from app.services.scheduler_service import scheduler_manager
    scheduler_manager.start()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Check status
        st = await client.get("/api/automation/status")
        assert st.status_code == 200
        assert len(st.json()["jobs"]) >= 6

        # Trigger on-demand
        run_res = await client.post("/api/automation/run/check_overdue_invoices")
        assert run_res.status_code == 200

        # Check logs
        logs = await client.get("/api/automation/logs?limit=5")
        assert logs.status_code == 200
        assert len(logs.json()["data"]) >= 1

@pytest.mark.asyncio
async def test_notification_delivery_and_unconfigured_fallback():
    from app.services.notification_service import NotificationService
    from app.models.schemas import NotificationCreate, NotificationType, NotificationChannel
    # In-app
    n1 = await NotificationService.create_notification(NotificationCreate(
        type=NotificationType.system,
        channel=NotificationChannel.in_app,
        title="Backup Done",
        message="Database backed up",
    ))
    assert n1["delivery_status"] == "unread"

    # Email unconfigured test: must NOT claim 'sent'
    n2 = await NotificationService.create_notification(NotificationCreate(
        type=NotificationType.reminder,
        channel=NotificationChannel.email,
        title="Payment Reminder",
        message="Please pay",
        recipient_email="test@domain.com",
    ))
    assert n2["delivery_status"] in ["unconfigured", "failed"]

@pytest.mark.asyncio
async def test_financial_intelligence_and_forecast():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/analytics/financial-intelligence")
        assert res.status_code == 200
        data = res.json()
        assert "monthly_revenue" in data
        assert "mom_comparison" in data
        assert "forecast" in data
        assert data["forecast"]["is_estimated"] is True

@pytest.mark.asyncio
async def test_rule_based_anomaly_detection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/analytics/anomalies")
        assert res.status_code == 200
        data = res.json()
        assert "anomalies_detected" in data
        assert len(data["anomalies"]) >= 1
        for a in data["anomalies"]:
            assert a["advisory_only"] is True

@pytest.mark.asyncio
async def test_ai_agent_automation_tools_and_confirmation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Upcoming query
        r1 = await client.post("/api/ai/chat", json={"message": "Show invoices due this week"})
        assert r1.status_code == 200
        assert any(t["tool_name"] == "get_upcoming_invoices" for t in r1.json().get("tools_executed", []))

        # 2. Anomaly query
        r2 = await client.post("/api/ai/chat", json={"message": "Find customers with repeated late payments"})
        assert r2.status_code == 200
        assert any(t["tool_name"] == "detect_anomalies" for t in r2.json().get("tools_executed", []))

        # 3. Forecast query
        r3 = await client.post("/api/ai/chat", json={"message": "Summarize my revenue this month and give me a revenue forecast"})
        assert r3.status_code == 200
        assert any(t["tool_name"] == "get_financial_analysis" for t in r3.json().get("tools_executed", []))

@pytest.mark.asyncio
async def test_phase7_production_database_guard():
    """Verify that in production mode, if DB is disconnected, health check returns 503 instead of masking it."""
    from app.core.config import settings
    from app.database import db_manager
    original_env = settings.environment
    original_connected = db_manager.is_connected
    try:
        settings.environment = "production"
        db_manager.is_connected = False
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get("/health")
            assert res.status_code == 503
            assert "unreachable in production" in res.json()["detail"].lower()
    finally:
        settings.environment = original_env
        db_manager.is_connected = original_connected

@pytest.mark.asyncio
async def test_phase7_end_to_end_payment_and_invoice_sync():
    """Workflow B: Verify complete invoice creation -> PayPal order creation -> Capture -> Invoice status updated to paid."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a customer
        cust_res = await client.post("/api/customers/", json={
            "name": "Phase 7 Enterprise Corp",
            "email": "finance@phase7corp.com",
            "company": "Phase 7 Enterprise",
        })
        cust_id = cust_res.json()["id"]

        # 2. Create an invoice
        inv_res = await client.post("/api/invoices/", json={
            "customer_id": cust_id,
            "items": [{"description": "Platform Modernization", "quantity": 1, "unit_price": 75000.0}],
            "tax_rate": 18.0,
            "due_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        })
        assert inv_res.status_code == 201
        inv_data = inv_res.json()
        inv_id = inv_data["id"]
        assert inv_data["status"] == "pending"

        # 3. Create PayPal Order
        order_res = await client.post("/api/payments/create-order", json={"invoice_id": inv_id})
        assert order_res.status_code == 201
        order_data = order_res.json()
        assert "order_id" in order_data
        paypal_order_id = order_data["order_id"]

        # 4. Capture PayPal Order (test capture prefix for sandbox simulator)
        cap_res = await client.post("/api/payments/capture-order", json={"order_id": f"TEST_{paypal_order_id}", "invoice_id": inv_id})
        assert cap_res.status_code == 200
        cap_data = cap_res.json()
        assert cap_data["status"].upper() == "COMPLETED"

        # 5. Verify Invoice in MongoDB is now PAID
        fetch_inv = await client.get(f"/api/invoices/{inv_id}")
        assert fetch_inv.status_code == 200
        updated_inv = fetch_inv.json()
        assert updated_inv["status"] == "paid"
        assert updated_inv["paid_date"] is not None

        # 6. Verify Transaction Record exists
        txns_res = await client.get(f"/api/transactions/?invoice_id={inv_id}")
        assert txns_res.status_code == 200
        txns = txns_res.json()["data"]
        assert len(txns) >= 1
        assert txns[0]["status"] == "completed"

@pytest.mark.asyncio
async def test_phase7_workflow_d_reminder_approval_e2e():
    """Workflow D: Verify reminder approval queue, dispatch, and state transition."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Create a reminder in pending_approval state
        rem_res = await client.post("/api/reminders/", json={
            "invoice_id": "inv_p7_test_01",
            "message": "Friendly reminder: your invoice is due soon.",
            "scheduled_date": datetime.now().strftime("%Y-%m-%d"),
            "status": "pending_approval",
        })
        assert rem_res.status_code == 201
        rem_data = rem_res.json()
        rem_id = rem_data["id"]

        # 2. Approve the reminder
        app_res = await client.post(f"/api/reminders/{rem_id}/approve", json={
            "reminder_id": rem_id,
            "approved": True,
            "channel": "in_app"
        })
        assert app_res.status_code == 200
        app_data = app_res.json()
        assert app_data["status"] in ["approved", "sent"]

        # 3. Verify notification was dispatched
        notifs_res = await client.get("/api/notifications/")
        assert notifs_res.status_code == 200
        notifs = notifs_res.json()["data"]
        assert any(n.get("reminder_id") == rem_id or "reminder" in n.get("title", "").lower() for n in notifs)






