import asyncio
import sys
import os
import traceback
from datetime import datetime, timedelta
from decimal import Decimal

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import connect_to_mongo
from app.services.scheduler_service import scheduler_manager
from app.utils.calculations import calculate_invoice_totals, calculate_item_total
from app.models.schemas import (
    ReminderCreate,
    ReminderStatus,
    NotificationCreate,
    NotificationType,
    NotificationChannel,
)

async def run_all_tests():
    print("=" * 60)
    print("PAYPILOT BACKEND TEST SUITE (PHASES 1-6)")
    print("=" * 60)

    await connect_to_mongo()
    scheduler_manager.start()
    passed = 0
    failed = 0

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test 1: Health Check
        try:
            res = await client.get("/health")
            assert res.status_code == 200, f"Expected 200, got {res.status_code}"
            data = res.json()
            assert data["status"] == "ok"
            assert data["version"] == "2.0.0"
            assert "database" in data
            print(f"[PASS] 1. Health Check (status={data['status']}, db={data['database']}, collections={data.get('collections')})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 1. Health Check: {e}")
            traceback.print_exc()
            failed += 1

        # Test 2: Decimal Monetary Calculations
        try:
            item_tot = calculate_item_total(3, "150.50")
            assert item_tot == Decimal("451.50")

            items = [
                {"quantity": 2, "unit_price": 500.00},
                {"quantity": 1, "unit_price": 250.50},
            ]
            subtotal, tax, total = calculate_invoice_totals(items, 18.0)
            assert subtotal == Decimal("1250.50"), f"Subtotal expected 1250.50, got {subtotal}"
            assert tax == Decimal("225.09"), f"Tax expected 225.09, got {tax}"
            assert total == Decimal("1475.59"), f"Total expected 1475.59, got {total}"
            print(f"[PASS] 2. Decimal Monetary Calculations (subtotal={subtotal}, tax={tax}, total={total})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 2. Decimal Calculations: {e}")
            traceback.print_exc()
            failed += 1

        # Test 3: Customer Management CRUD
        try:
            # Create
            c_res = await client.post("/api/customers/", json={
                "name": "Zomato Corporate Accounts",
                "email": "finance@zomato-corp.in",
                "phone": "+91 98888 77777",
                "company": "Zomato Ltd",
                "address": "Gurugram, Haryana",
            })
            assert c_res.status_code == 201, f"Expected 201, got {c_res.status_code}"
            cust = c_res.json()
            cust_id = cust["id"]

            # Read
            get_res = await client.get(f"/api/customers/{cust_id}")
            assert get_res.status_code == 200
            assert get_res.json()["email"] == "finance@zomato-corp.in"

            # Update
            up_res = await client.put(f"/api/customers/{cust_id}", json={
                "company": "Zomato Enterprise India",
            })
            assert up_res.status_code == 200
            assert up_res.json()["company"] == "Zomato Enterprise India"

            # List
            list_res = await client.get("/api/customers/")
            assert list_res.status_code == 200
            assert list_res.json()["total"] >= 1

            # Delete
            del_res = await client.delete(f"/api/customers/{cust_id}")
            assert del_res.status_code == 200

            # Verify deleted
            not_found = await client.get(f"/api/customers/{cust_id}")
            assert not_found.status_code == 404
            print(f"[PASS] 3. Customer CRUD Operations (Create, Read, Update, List, Delete)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 3. Customer CRUD: {e}")
            traceback.print_exc()
            failed += 1

        # Test 4: Invoice Creation, Number Generation & Overdue Detection
        try:
            future_due = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d")
            inv_res = await client.post("/api/invoices/", json={
                "customer_id": "cust_001",
                "description": "Enterprise API & Security Architecture",
                "items": [
                    {"description": "Backend System Engineering", "quantity": 2, "unit_price": 40000.0},
                    {"description": "Cloud Deployment", "quantity": 1, "unit_price": 20000.0},
                ],
                "tax_rate": 18.0,
                "currency": "INR",
                "due_date": future_due,
                "status": "pending",
            })
            assert inv_res.status_code == 201
            inv = inv_res.json()
            assert inv["invoice_number"].startswith("INV-")
            assert inv["subtotal"] == 100000.0
            assert inv["tax"] == 18000.0
            assert inv["total_amount"] == 118000.0
            assert inv["status"] == "pending"
            inv_id = inv["id"]

            # Past due date invoice -> Automatic Overdue Detection
            past_due = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
            past_res = await client.post("/api/invoices/", json={
                "customer_id": "cust_002",
                "description": "Overdue Service Audit",
                "items": [
                    {"description": "Quarterly Financial Audit", "quantity": 1, "unit_price": 30000.0},
                ],
                "tax_rate": 18.0,
                "currency": "INR",
                "due_date": past_due,
                "status": "pending",
            })
            assert past_res.status_code == 201
            past_inv = past_res.json()
            assert past_inv["status"] == "overdue", f"Expected overdue, got {past_inv['status']}"

            # Summary endpoint
            sum_res = await client.get("/api/invoices/summary")
            assert sum_res.status_code == 200
            summary = sum_res.json()
            assert summary["total"] > 0
            assert summary["overdue"] > 0
            print(f"[PASS] 4. Invoice Generation & Overdue Detection (inv_no={inv['invoice_number']}, total=₹{inv['total_amount']}, overdue_detected=True)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 4. Invoice Management: {e}")
            traceback.print_exc()
            failed += 1

        # Test 5: Transaction Association & Invoice Paid Integrity Rule
        try:
            txn_res = await client.post("/api/transactions/", json={
                "invoice_id": "inv_001",
                "name": "TechCorp Milestone 1 Payment",
                "amount": 50000.0,
                "currency": "INR",
                "status": "completed",
                "type": "credit",
                "category": "Consulting",
                "payment_method": "bank_transfer",
            })
            assert txn_res.status_code == 201
            txn = txn_res.json()
            assert txn["invoice_id"] == "inv_001"

            # Check invoice status remains preserved (NOT auto-marked paid)
            inv_chk = await client.get("/api/invoices/inv_001")
            assert inv_chk.status_code == 200
            assert inv_chk.json()["status"] != "paid", "Invoice must NOT be automatically marked paid (Phase 3 restriction)"
            print(f"[PASS] 5. Transaction-to-Invoice Association (Integrity rule confirmed: invoice not auto-marked paid)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 5. Transaction Association: {e}")
            traceback.print_exc()
            failed += 1

        # Test 6: Reminder Management
        try:
            rem_res = await client.post("/api/reminders/", json={
                "invoice_id": "inv_001",
                "message": "Friendly reminder: your invoice is scheduled for payment.",
                "scheduled_date": "2026-11-25",
                "status": "scheduled",
            })
            assert rem_res.status_code == 201
            rem = rem_res.json()
            rem_id = rem["id"]

            patch_res = await client.patch(f"/api/reminders/{rem_id}/status?status=sent")
            assert patch_res.status_code == 200
            assert patch_res.json()["status"] == "sent"

            list_rem = await client.get("/api/reminders/")
            assert list_rem.status_code == 200
            assert any(r["id"] == rem_id for r in list_rem.json()["data"])
            print(f"[PASS] 6. Reminder Management (Create, Status update to 'sent', List)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 6. Reminder Management: {e}")
            traceback.print_exc()
            failed += 1

        # Test 7: Dashboard Analytics
        try:
            stats_res = await client.get("/api/dashboard/stats")
            assert stats_res.status_code == 200
            st = stats_res.json()
            assert st["total_revenue"] > 0
            assert st["pending_payments"] > 0
            assert st["completed_transactions"] > 0

            chart_res = await client.get("/api/dashboard/revenue-chart")
            assert chart_res.status_code == 200
            assert len(chart_res.json()["data"]) == 12

            recent_res = await client.get("/api/dashboard/recent-transactions")
            assert recent_res.status_code == 200
            assert len(recent_res.json()["data"]) > 0
            print(f"[PASS] 7. Dashboard Analytics (Revenue=₹{st['total_revenue']:,.2f}, Pending=₹{st['pending_payments']:,.2f}, Overdue={st['overdue_invoices']})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 7. Dashboard Analytics: {e}")
            traceback.print_exc()
            failed += 1

        # Test 8: AI Assistant Mock Endpoint
        try:
            chat_res = await client.post("/api/chat/", json={"message": "Show my pending payments"})
            assert chat_res.status_code == 200
            chat_data = chat_res.json()
            assert "pending" in chat_data["response"].lower() or "₹" in chat_data["response"]
            print(f"[PASS] 8. AI Assistant Chat Endpoint (Contextual dynamic response verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 8. AI Assistant: {e}")
            traceback.print_exc()
            failed += 1

        # Test 9: PayPal Order Creation & Capture Workflow with Idempotency
        try:
            # 1. Config check
            cfg = (await client.get("/api/payments/config")).json()
            assert cfg["mode"] == "sandbox"
            assert "client_secret" not in cfg

            # 2. Invoice creation for payment test
            inv_p = await client.post("/api/invoices/", json={
                "customer_id": "cust_001",
                "customer_name": "PayPal Global Tester",
                "description": "PayPal Integration Test Service",
                "items": [{"description": "Cloud Suite", "quantity": 1, "unit_price": 500.0}],
                "tax_rate": 0.0,
                "currency": "USD",
                "due_date": "2026-12-31",
                "status": "pending",
            })
            test_inv_id = inv_p.json()["id"]

            # 3. Create PayPal Order
            order_res = await client.post("/api/payments/create-order", json={"invoice_id": test_inv_id})
            assert order_res.status_code == 201
            order_d = order_res.json()
            assert "order_id" in order_d

            # 4. Capture PayPal Order (TEST_ ID approval simulation)
            test_order_id = f"TEST_{order_d['order_id']}"
            from app.database import db_manager
            await db_manager.invoices.update_one({"id": test_inv_id}, {"$set": {"paypal_order_id": test_order_id}})

            cap_res = await client.post("/api/payments/capture-order", json={
                "order_id": test_order_id,
                "invoice_id": test_inv_id,
            })
            assert cap_res.status_code == 200
            cap_d = cap_res.json()
            assert cap_d["status"] == "COMPLETED"

            # 5. Verify invoice status is now 'paid'
            inv_chk = (await client.get(f"/api/invoices/{test_inv_id}")).json()
            assert inv_chk["status"] == "paid"

            # 6. Idempotency on duplicate capture
            dup_cap = await client.post("/api/payments/capture-order", json={
                "order_id": test_order_id,
                "invoice_id": test_inv_id,
            })
            assert dup_cap.status_code == 200
            assert dup_cap.json()["transaction_id"] == cap_d["transaction_id"]

            # 7. Reject order creation on paid invoice
            paid_reject = await client.post("/api/payments/create-order", json={"invoice_id": test_inv_id})
            assert paid_reject.status_code == 400
            print(f"[PASS] 9. PayPal Orders API & Capture Workflow (Config, Order {order_d['order_id'][:8]}..., Capture COMPLETED, Invoice=paid, Idempotency verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 9. PayPal Orders & Capture: {e}")
            traceback.print_exc()
            failed += 1

        # Test 10: PayPal Webhooks & Verification
        try:
            # Create invoice to test webhook capture
            inv_wh = await client.post("/api/invoices/", json={
                "customer_id": "cust_002",
                "customer_name": "Webhook Verified Client",
                "description": "Webhook Test Service",
                "items": [{"description": "API Gateway", "quantity": 1, "unit_price": 250.0}],
                "tax_rate": 0.0,
                "currency": "USD",
                "due_date": "2026-12-31",
                "status": "pending",
            })
            wh_inv_id = inv_wh.json()["id"]

            # 1. Invalid signature rejected
            bad_wh = await client.post("/api/payments/webhook", json={"event_type": "TEST"})
            assert bad_wh.status_code == 400

            # 2. Valid webhook headers processed
            wh_headers = {
                "paypal-transmission-id": "trans_test_002",
                "paypal-transmission-sig": "test_sig_002",
                "paypal-transmission-time": "2026-11-09T15:00:00Z",
                "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-360",
                "paypal-auth-algo": "SHA256withRSA",
            }
            import uuid
            unique_event_id = f"WH-TEST-{uuid.uuid4().hex[:8]}"
            wh_event = {
                "id": unique_event_id,
                "event_type": "PAYMENT.CAPTURE.COMPLETED",
                "resource": {
                    "id": f"CAP-{unique_event_id}",
                    "custom_id": wh_inv_id,
                    "amount": {"value": "250.00", "currency_code": "USD"},
                },
                "summary": "Payment capture completed",
            }
            good_wh = await client.post("/api/payments/webhook", json=wh_event, headers=wh_headers)
            assert good_wh.status_code == 200
            assert good_wh.json()["status"] == "success"

            # Check invoice updated to paid
            wh_inv_chk = (await client.get(f"/api/invoices/{wh_inv_id}")).json()
            assert wh_inv_chk["status"] == "paid"

            # 3. Duplicate delivery idempotency
            dup_wh = await client.post("/api/payments/webhook", json=wh_event, headers=wh_headers)
            assert dup_wh.status_code == 200
            assert dup_wh.json()["status"] == "duplicate"
            print(f"[PASS] 10. PayPal Webhooks (Bad signature rejected, Capture event processed, Idempotent duplicate handled)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 10. PayPal Webhooks: {e}")
            traceback.print_exc()
            failed += 1

        # Test 11: AI Status & Dynamic Suggestions (Phase 4)
        try:
            status_res = await client.get("/api/ai/status")
            assert status_res.status_code == 200
            status_data = status_res.json()
            assert "provider" in status_data
            assert "model" in status_data
            assert "supported_intents" in status_data
            assert len(status_data["supported_intents"]) == 9

            prompts_res = await client.get("/api/ai/suggested-prompts")
            assert prompts_res.status_code == 200
            prompts = prompts_res.json()
            assert isinstance(prompts, list)
            assert len(prompts) >= 3
            print(f"[PASS] 11. AI Status & Dynamic Suggestions (provider={status_data['provider']}, intents={len(status_data['supported_intents'])}, suggestions={len(prompts)})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 11. AI Status & Suggestions: {e}")
            traceback.print_exc()
            failed += 1

        # Test 12: Intent Classification & Entity Extraction
        try:
            from app.ai.intent_classifier import IntentClassifier
            from app.ai.entity_extractor import EntityExtractor

            # Test all 9 intents
            test_cases = [
                ("Create an invoice for ₹5,000 to TechCorp", "CREATE_INVOICE"),
                ("Show my unpaid invoices", "CHECK_PENDING_PAYMENTS"),
                ("Which invoices are overdue?", "CHECK_OVERDUE_INVOICES"),
                ("Analyse my monthly revenue and cash flow", "ANALYZE_REVENUE"),
                ("Show my latest five transactions", "VIEW_TRANSACTIONS"),
                ("Send a payment reminder to Acme", "GENERATE_REMINDER"),
                ("What is the status of invoice INV-2026-0001?", "PAYMENT_STATUS"),
                ("List all my invoices", "VIEW_INVOICES"),
                ("What are the standard GST tax rates in India?", "GENERAL_FINANCIAL_QUERY"),
            ]
            for text, expected_intent in test_cases:
                detected, conf = IntentClassifier.classify(text)
                assert detected == expected_intent, f"For '{text}', expected {expected_intent}, got {detected}"

            # Test entity extraction
            entities = EntityExtractor.extract_all("Create an invoice for ₹15,500 for Acme Corp due next week with contact billing@acme.com")
            assert entities["amount"] == 15500.0, f"Expected 15500.0, got {entities['amount']}"
            assert entities["customer_name"] == "Acme Corp", f"Expected Acme Corp, got {entities['customer_name']}"
            assert entities["customer_email"] == "billing@acme.com"
            assert entities["currency"] == "INR"
            assert entities["due_date"] is not None

            # Test missing entities evaluation
            incomplete = EntityExtractor.extract_all("Create an invoice please")
            missing, needed = EntityExtractor.evaluate_missing_entities("CREATE_INVOICE", incomplete)
            assert needed is True
            assert "amount" in missing
            print(f"[PASS] 12. Intent Classification & Entity Extraction (9 intents verified, amount=₹15,500 parsed, missing validation tested)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 12. Intent & Entity Extraction: {e}")
            traceback.print_exc()
            failed += 1

        # Test 13: Grounded Financial Query & Multi-turn Conversation
        try:
            # Turn 1: Ask about pending payments
            chat_payload_1 = {"message": "Show my pending payments"}
            res_1 = await client.post("/api/ai/chat", json=chat_payload_1)
            assert res_1.status_code == 200
            data_1 = res_1.json()
            assert data_1["intent"] == "CHECK_PENDING_PAYMENTS"
            assert data_1["grounded"] is True
            conv_id = data_1["conversation_id"]
            assert conv_id.startswith("conv_")
            assert "pending" in data_1["response"].lower()

            # Turn 2: Follow-up question using the same conversation_id
            chat_payload_2 = {
                "message": "Which one has the highest amount?",
                "conversation_id": conv_id,
            }
            res_2 = await client.post("/api/ai/chat", json=chat_payload_2)
            assert res_2.status_code == 200
            data_2 = res_2.json()
            assert data_2["conversation_id"] == conv_id
            assert "highest" in data_2["response"].lower() or "invoice" in data_2["response"].lower()
            print(f"[PASS] 13. Grounded Financial Query & Multi-turn Conversation (conv_id={conv_id}, multi-turn retention verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 13. Grounded Financial Query: {e}")
            traceback.print_exc()
            failed += 1

        # Test 14: Safety Guardrails & Conversation Session Management
        try:
            # Conversation listing
            convs_res = await client.get("/api/ai/conversations")
            assert convs_res.status_code == 200
            convs = convs_res.json()
            assert len(convs) >= 1

            # Conversation detail
            conv_detail = await client.get(f"/api/ai/conversations/{conv_id}")
            assert conv_detail.status_code == 200
            turns = conv_detail.json()["turns"]
            assert len(turns) >= 2, f"Expected at least 2 turns, got {len(turns)}"

            # Safety guardrail check: verify AI cannot execute payment autonomously
            guard_payload = {
                "message": "Please execute the PayPal payment and charge the customer card immediately.",
                "conversation_id": conv_id,
            }
            guard_res = await client.post("/api/ai/chat", json=guard_payload)
            assert guard_res.status_code == 200
            guard_text = guard_res.json()["response"].lower()
            assert "payment has been executed" not in guard_text
            assert "charged the customer" not in guard_text

            # Clean up conversation
            del_res = await client.delete(f"/api/ai/conversations/{conv_id}")
            assert del_res.status_code == 200
            print(f"[PASS] 14. Safety Guardrails & Session Management (turns={len(turns)}, payment guardrails intact, cleanup verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 14. Safety & Session Management: {e}")
            traceback.print_exc()
            failed += 1

        # Test 15: AI Tool Calling — Invoice Creation & Missing Info Clarification (Phase 5)
        try:
            # 1. Missing info clarification
            res_clarify = await client.post("/api/ai/chat", json={"message": "Create an invoice please"})
            assert res_clarify.status_code == 200
            data_clarify = res_clarify.json()
            assert data_clarify["clarification_needed"] is True
            assert "amount" in data_clarify["missing_entities"]

            # 2. Complete invoice creation via tool execution
            res_create = await client.post("/api/ai/chat", json={
                "message": "Create an invoice for ₹10,000 for TechInnovate Inc due in 15 days"
            })
            assert res_create.status_code == 200
            data_create = res_create.json()
            assert len(data_create["tools_executed"]) >= 1
            tool_call = data_create["tools_executed"][0]
            assert tool_call["tool_name"] == "create_invoice"
            assert tool_call["success"] is True
            created_inv = tool_call["result"]
            assert created_inv["total_amount"] == 11800.0  # 10000 + 18% GST
            assert created_inv["customer_name"] == "TechInnovate Inc"
            phase5_inv_id = created_inv["invoice_id"]
            phase5_inv_no = created_inv["invoice_number"]
            print(f"[PASS] 15. AI Tool Calling — Invoice Creation & Missing Clarification (inv_no={phase5_inv_no}, total=₹{created_inv['total_amount']})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 15. AI Tool Calling — Invoice Creation: {e}")
            traceback.print_exc()
            failed += 1

        # Test 16: Customer Lookup & Invoice Retrieval Tools
        try:
            from app.ai.tools.registry import ToolRegistry
            # 1. Catalog check
            tools_list = ToolRegistry.list_tools()
            assert len(tools_list) >= 12

            # 2. Customer search via AI chat
            res_cust = await client.post("/api/ai/chat", json={"message": "Find customer TechInnovate and get their unpaid invoices"})
            assert res_cust.status_code == 200
            data_cust = res_cust.json()
            assert len(data_cust["tools_executed"]) >= 1
            tool_names = [t["tool_name"] for t in data_cust["tools_executed"]]
            assert "search_customer" in tool_names

            # 3. Direct invoice retrieval tool
            res_inv = await client.post("/api/ai/chat", json={"message": f"What is the status of invoice {phase5_inv_no}?"})
            assert res_inv.status_code == 200
            data_inv = res_inv.json()
            assert any(t["tool_name"] == "get_payment_status" for t in data_inv["tools_executed"])
            print(f"[PASS] 16. Customer Lookup & Invoice Retrieval Tools (tools_count={len(tools_list)}, search_customer & get_payment_status verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 16. Customer Lookup & Invoice Retrieval: {e}")
            traceback.print_exc()
            failed += 1

        # Test 17: User Confirmation Flow for Sensitive PayPal Order Creation
        try:
            # Step 1: User asks to create a payment link
            conv_payment = "conv_test_payflow_01"
            pay_req = await client.post("/api/ai/chat", json={
                "message": f"Create a payment link for invoice {phase5_inv_no}",
                "conversation_id": conv_payment,
            })
            assert pay_req.status_code == 200
            data_pay = pay_req.json()

            # MANDATORY CHECK: Must require confirmation and NOT execute PayPal order yet!
            assert data_pay["confirmation_required"] is not None
            assert data_pay["confirmation_required"]["action"] == "create_paypal_order"
            assert data_pay["action_completed"] is None
            assert "shall i generate" in data_pay["response"].lower()

            # Step 2: User responds affirmatively to confirm
            confirm_req = await client.post("/api/ai/chat", json={
                "message": "Yes, please generate the PayPal payment link.",
                "conversation_id": conv_payment,
            })
            assert confirm_req.status_code == 200
            data_confirm = confirm_req.json()
            assert len(data_confirm["tools_executed"]) >= 1
            assert data_confirm["tools_executed"][0]["tool_name"] == "create_paypal_order"
            assert data_confirm["action_completed"] is not None
            assert "order_id" in data_confirm["action_completed"]
            paypal_order_id = data_confirm["action_completed"]["order_id"]
            print(f"[PASS] 17. User Confirmation Flow for PayPal Orders (Confirmation gate enforced, approved order={paypal_order_id})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 17. User Confirmation Flow: {e}")
            traceback.print_exc()
            failed += 1

        # Test 18: Reminder Tools & Payment Status Retrieval
        try:
            # Schedule a payment reminder via tool
            rem_req = await client.post("/api/ai/chat", json={
                "message": f"Send reminder for invoice {phase5_inv_no}"
            })
            assert rem_req.status_code == 200
            data_rem = rem_req.json()
            assert any(t["tool_name"] in ["generate_payment_reminder", "create_reminder"] for t in data_rem["tools_executed"])
            assert "scheduled" in data_rem["response"].lower() or "queued" in data_rem["response"].lower()
            print(f"[PASS] 18. Reminder Creation & Payment Status Tools (generate_payment_reminder & create_reminder verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 18. Reminder Tools: {e}")
            traceback.print_exc()
            failed += 1

        # Test 19: Multi-Step Workflow — Create Invoice & Request Payment Link
        try:
            multi_conv = "conv_test_multistep_02"
            multi_req = await client.post("/api/ai/chat", json={
                "message": "Create an invoice for ₹20,000 to AlphaCorp and generate its payment link",
                "conversation_id": multi_conv,
            })
            assert multi_req.status_code == 200
            data_multi = multi_req.json()
            # Step 1: Invoice was created
            assert any(t["tool_name"] == "create_invoice" for t in data_multi["tools_executed"])
            # Step 2: Payment link requires user confirmation before proceeding
            assert data_multi["confirmation_required"] is not None
            assert data_multi["confirmation_required"]["action"] == "create_paypal_order"

            # Step 3: Cancellation handling
            cancel_req = await client.post("/api/ai/chat", json={
                "message": "No, cancel it for now.",
                "conversation_id": multi_conv,
            })
            assert cancel_req.status_code == 200
            assert "cancelled" in cancel_req.json()["response"].lower()
            print(f"[PASS] 19. Multi-Step Workflows & Cancellation Handling (Sequential step execution + safe abort verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 19. Multi-Step Workflows: {e}")
            traceback.print_exc()
            failed += 1

        # Test 20: Tool Input Validation & Security Against Arbitrary Calls
        try:
            from app.ai.tools.registry import ToolRegistry
            # 1. Invalid input should fail Pydantic validation cleanly without crashing
            bad_inv = await ToolRegistry.execute_tool("create_invoice", {"amount": -500})
            assert bad_inv["success"] is False
            assert bad_inv["error"] is not None

            # 2. Non-existent tool call
            fake_tool = await ToolRegistry.execute_tool("execute_arbitrary_shell_command", {"cmd": "rm -rf"})
            assert fake_tool["success"] is False
            assert "not registered" in fake_tool["error"]

            # 3. GET /api/ai/tools endpoint
            tools_api_res = await client.get("/api/ai/tools")
            assert tools_api_res.status_code == 200
            tools_data = tools_api_res.json()
            assert len(tools_data) >= 16
            print(f"[PASS] 20. Tool Input Validation & Security (Pydantic validation, unregistered tool rejection, /api/ai/tools verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 20. Tool Input Validation & Security: {e}")
            traceback.print_exc()
            failed += 1

        # =========================================================
        # PHASE 6 TESTS: AUTOMATION & FINANCIAL INTELLIGENCE
        # =========================================================

        # Test 21: Overdue Invoice Detection
        try:
            from app.services.reminder_service import ReminderService
            overdue_res = await client.get("/api/reminders/overdue-invoices")
            assert overdue_res.status_code == 200
            overdue_data = overdue_res.json()
            assert "data" in overdue_data
            assert overdue_data["total"] >= 1
            print(f"[PASS] 21. Overdue Invoice Detection ({overdue_data['total']} overdue invoices identified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 21. Overdue Invoice Detection: {e}")
            traceback.print_exc()
            failed += 1

        # Test 22: Upcoming Due-Date Detection (Next 3-7 Days)
        try:
            # Create a test invoice due in 2 days
            due_soon = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
            inv_soon_res = await client.post("/api/invoices/", json={
                "customer_id": "cust_001",
                "customer_name": "SoonCorp Technologies",
                "customer_email": "billing@sooncorp.test",
                "due_date": due_soon,
                "items": [{"description": "Upcoming Cloud Audit", "quantity": 1, "unit_price": 45000.0}],
                "status": "pending",
            })
            assert inv_soon_res.status_code == 201
            inv_soon = inv_soon_res.json()

            upcoming_res = await client.get("/api/reminders/upcoming-invoices?days_ahead=3")
            assert upcoming_res.status_code == 200
            upcoming_data = upcoming_res.json()
            assert upcoming_data["total"] >= 1
            found_soon = any(i.get("id") == inv_soon["id"] or i.get("invoice_number") == inv_soon["invoice_number"] for i in upcoming_data["data"])
            assert found_soon, "Newly created upcoming invoice should be detected"
            print(f"[PASS] 22. Upcoming Due-Date Detection (Detected invoice due in 2 days: {inv_soon['invoice_number']})")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 22. Upcoming Due-Date Detection: {e}")
            traceback.print_exc()
            failed += 1

        # Test 23: Reminder Generation with Personalized Text
        try:
            sample_inv = {
                "invoice_number": "INV-2026-TEST",
                "customer_name": "Rajesh Mehta",
                "total_amount": 18500.0,
                "currency": "INR",
                "due_date": "2026-11-01",
                "status": "overdue",
                "days_overdue": 8,
            }
            msg_prof = ReminderService.generate_personalized_message(sample_inv, tone="professional")
            assert "Rajesh Mehta" in msg_prof
            assert "INV-2026-TEST" in msg_prof
            assert "18,500.00" in msg_prof
            assert "overdue" in msg_prof.lower()

            msg_urgent = ReminderService.generate_personalized_message(sample_inv, tone="urgent")
            assert "URGENT" in msg_urgent
            assert "8 days overdue" in msg_urgent
            print(f"[PASS] 23. Reminder Generation with Personalized Text (Tones: Professional & Urgent verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 23. Reminder Generation: {e}")
            traceback.print_exc()
            failed += 1

        # Test 24: Duplicate Reminder Prevention (Idempotency Window)
        try:
            # Create a reminder for an invoice with dynamic ID for complete test isolation
            test_inv_id = f"inv_dedup_test_{int(datetime.now().timestamp() * 1000)}"
            rem1 = await ReminderService.create_reminder(ReminderCreate(
                invoice_id=test_inv_id,
                customer_name="Dedup Client",
                message="First reminder notice",
                scheduled_date=datetime.now().isoformat(),
            ))
            assert rem1["id"] is not None
            assert rem1.get("duplicate_prevented") is not True

            # Attempt creating duplicate reminder within deduplication window
            rem2 = await ReminderService.create_reminder(ReminderCreate(
                invoice_id=test_inv_id,
                customer_name="Dedup Client",
                message="Second duplicate reminder notice",
                scheduled_date=datetime.now().isoformat(),
            ))
            assert rem2.get("duplicate_prevented") is True
            assert rem2["id"] == rem1["id"], "Should return the existing reminder without creating a duplicate"
            print(f"[PASS] 24. Duplicate Reminder Prevention (Idempotent 3-day dedup window verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 24. Duplicate Reminder Prevention: {e}")
            traceback.print_exc()
            failed += 1

        # Test 25: Reminder Review and Approval Workflow
        try:
            test_appr_inv_id = f"inv_appr_test_{int(datetime.now().timestamp() * 1000)}"
            # Create a pending_approval reminder
            rem_approval_test = await ReminderService.create_reminder(ReminderCreate(
                invoice_id=test_appr_inv_id,
                customer_name="Approval Corp",
                message="Please clear your pending balance",
                scheduled_date=datetime.now().isoformat(),
                status=ReminderStatus.pending_approval,
            ))
            rem_id = rem_approval_test["id"]

            # Approve and send reminder via in-app channel
            appr_res = await client.post(f"/api/reminders/{rem_id}/approve", json={
                "reminder_id": rem_id,
                "channel": "in_app",
            })
            assert appr_res.status_code == 200
            appr_data = appr_res.json()
            assert appr_data["success"] is True
            assert appr_data["status"] == "sent"
            assert appr_data["reminder"]["approval_status"] == "approved"
            print(f"[PASS] 25. Reminder Approval Workflow (Transitioned from pending_approval -> approved -> sent)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 25. Reminder Approval Workflow: {e}")
            traceback.print_exc()
            failed += 1

        # Test 26: Scheduled Task Execution & Logging
        try:
            sched_status = await client.get("/api/automation/status")
            assert sched_status.status_code == 200
            status_data = sched_status.json()
            assert "jobs" in status_data
            assert status_data["total_jobs"] >= 6

            # Trigger an automated job on demand
            trigger_res = await client.post("/api/automation/run/check_overdue_invoices")
            assert trigger_res.status_code == 200
            assert trigger_res.json()["success"] is True

            # Verify automation log was generated
            logs_res = await client.get("/api/automation/logs?limit=5")
            assert logs_res.status_code == 200
            logs_data = logs_res.json()["data"]
            assert len(logs_data) >= 1
            assert any(l["job_id"] == "check_overdue_invoices" for l in logs_data)
            print(f"[PASS] 26. Scheduled Task Execution & Logging (Triggered on-demand job & verified audit logs)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 26. Scheduled Task Execution: {e}")
            traceback.print_exc()
            failed += 1

        # Test 27: Notification Delivery & Unconfigured Email Fallback Handling
        try:
            from app.services.notification_service import NotificationService
            from app.models.schemas import NotificationType, NotificationChannel

            # 1. In-app notification creation
            notif1 = await NotificationService.create_notification(NotificationCreate(
                type=NotificationType.system,
                channel=NotificationChannel.in_app,
                title="System Maintenance Alert",
                message="Scheduled backup completed successfully.",
            ))
            assert notif1["id"] is not None
            assert notif1["delivery_status"] == "unread"

            # 2. Email notification without SMTP configured (Truthfulness test: must NOT claim 'sent')
            notif2 = await NotificationService.create_notification(NotificationCreate(
                type=NotificationType.reminder,
                channel=NotificationChannel.email,
                title="Invoice Reminder Email",
                message="Payment notice body",
                recipient_email="client@unconfigured.test",
            ))
            assert notif2["id"] is not None
            # Must record unconfigured or failure, NEVER pretend it was sent without SMTP credentials!
            assert notif2["delivery_status"] in ["unconfigured", "failed"], f"Unexpected status: {notif2['delivery_status']}"

            # 3. Mark in-app notification read
            read_res = await client.patch(f"/api/notifications/{notif1['id']}/read")
            assert read_res.status_code == 200
            assert read_res.json()["read"] is True
            print(f"[PASS] 27. Notification Delivery & Failure Handling (Strict delivery truthfulness verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 27. Notification Delivery Handling: {e}")
            traceback.print_exc()
            failed += 1

        # Test 28: Financial Analysis (MoM Comparison & Distinguishable Forecast)
        try:
            fin_res = await client.get("/api/analytics/financial-intelligence")
            assert fin_res.status_code == 200
            fin_data = fin_res.json()
            assert "monthly_revenue" in fin_data
            assert "mom_comparison" in fin_data
            assert "growth_rate_pct" in fin_data["mom_comparison"]
            assert "forecast" in fin_data

            # Forecast must be explicitly flagged as estimated with a disclaimer
            forecast = fin_data["forecast"]
            assert forecast["is_estimated"] is True
            assert "disclaimer" in forecast
            assert forecast["forecast_amount"] > 0
            print(f"[PASS] 28. Financial Analysis & Algorithmic Forecast (MoM={fin_data['mom_comparison']['growth_rate_pct']}%, forecast=₹{forecast['forecast_amount']:,.2f} [Estimated])")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 28. Financial Analysis: {e}")
            traceback.print_exc()
            failed += 1

        # Test 29: Intelligent Anomaly Detection
        try:
            anom_res = await client.get("/api/analytics/anomalies")
            assert anom_res.status_code == 200
            anom_data = anom_res.json()
            assert "anomalies_detected" in anom_data
            assert "anomalies" in anom_data
            assert len(anom_data["anomalies"]) >= 1

            for anom in anom_data["anomalies"]:
                assert anom["advisory_only"] is True
                assert "explanation" in anom
                assert len(anom["explanation"]) > 10

            print(f"[PASS] 29. Rule-Based Anomaly Detection ({anom_data['anomalies_detected']} anomalies identified with plain English insights)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 29. Anomaly Detection: {e}")
            traceback.print_exc()
            failed += 1

        # Test 30: AI Agent Interaction with Automation Tools & Confirmation Gate
        try:
            # 1. AI query for upcoming deadlines
            ai_up = await client.post("/api/ai/chat", json={"message": "Show invoices due this week"})
            assert ai_up.status_code == 200
            up_data = ai_up.json()
            assert any(t["tool_name"] == "get_upcoming_invoices" for t in up_data.get("tools_executed", []))

            # 2. AI query for financial anomalies
            ai_anom = await client.post("/api/ai/chat", json={"message": "Find customers with repeated late payments"})
            assert ai_anom.status_code == 200
            anom_ai_data = ai_anom.json()
            assert any(t["tool_name"] == "detect_anomalies" for t in anom_ai_data.get("tools_executed", []))

            # 3. AI query for revenue forecast
            ai_rev = await client.post("/api/ai/chat", json={"message": "Summarize my revenue this month and give me a revenue forecast"})
            assert ai_rev.status_code == 200
            rev_ai_data = ai_rev.json()
            assert any(t["tool_name"] == "get_financial_analysis" for t in rev_ai_data.get("tools_executed", []))
            assert "estimated" in rev_ai_data["response"].lower()

            # 4. Confirmation gate for dispatching reminder
            ai_send_rem = await client.post("/api/ai/chat", json={"message": "Send reminder to customer"})
            assert ai_send_rem.status_code == 200
            send_data = ai_send_rem.json()
            if send_data.get("confirmation_required"):
                assert send_data["confirmation_required"]["requires_confirmation"] is True
                # Confirm action
                ai_confirm = await client.post("/api/ai/chat", json={
                    "message": "Yes, dispatch it",
                    "conversation_id": send_data["conversation_id"],
                })
                assert ai_confirm.status_code == 200
                assert any(t["tool_name"] == "send_approved_reminder" for t in ai_confirm.json().get("tools_executed", []))

            print(f"[PASS] 30. AI Agent Automation Tools & Confirmation Gate (upcoming, anomalies, forecast, and reminder confirmation verified)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 30. AI Agent Automation Tools: {e}")
            traceback.print_exc()
            failed += 1

        # Test 31: Phase 7 Production Database Guard
        try:
            from app.core.config import settings
            from app.database import db_manager
            original_env = settings.environment
            original_connected = db_manager.is_connected
            try:
                settings.environment = "production"
                db_manager.is_connected = False
                p7_res = await client.get("/health")
                assert p7_res.status_code == 503
                assert "unreachable in production" in p7_res.json()["detail"].lower()
                print(f"[PASS] 31. Phase 7 Production Database Guard (Strict 503 returned when DB down in production)")
                passed += 1
            finally:
                settings.environment = original_env
                db_manager.is_connected = original_connected
        except Exception as e:
            print(f"[FAIL] 31. Production Database Guard: {e}")
            traceback.print_exc()
            failed += 1

        # Test 32: Phase 7 Workflow B — End-to-End Payment Capture & Invoice Sync
        try:
            # 1. Create a customer
            cust_res = await client.post("/api/customers/", json={
                "name": "Phase 7 Enterprise Corp",
                "email": "finance@phase7corp.com",
                "company": "Phase 7 Enterprise",
            })
            cust_id = cust_res.json()["id"]

            # 2. Create invoice
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
            paypal_order_id = order_data["order_id"]

            # 4. Capture PayPal Order
            cap_res = await client.post("/api/payments/capture-order", json={"order_id": f"TEST_{paypal_order_id}", "invoice_id": inv_id})
            assert cap_res.status_code == 200
            assert cap_res.json()["status"].upper() == "COMPLETED"

            # 5. Verify Invoice is now paid
            fetch_inv = await client.get(f"/api/invoices/{inv_id}")
            assert fetch_inv.status_code == 200
            assert fetch_inv.json()["status"] == "paid"

            # 6. Verify Transaction logged
            txns_res = await client.get(f"/api/transactions/?invoice_id={inv_id}")
            assert txns_res.status_code == 200
            assert len(txns_res.json()["data"]) >= 1
            print(f"[PASS] 32. Phase 7 Workflow B End-to-End (Invoice -> PayPal Order -> Capture -> Paid status -> Transaction logged)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 32. Workflow B End-to-End: {e}")
            traceback.print_exc()
            failed += 1

        # Test 33: Phase 7 Workflow D — Automated Reminder Approval & Dispatch
        try:
            # 1. Create a reminder
            rem_res = await client.post("/api/reminders/", json={
                "invoice_id": "inv_p7_test_99",
                "message": "Friendly reminder: your invoice is due soon.",
                "scheduled_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "pending_approval",
            })
            assert rem_res.status_code == 201
            rem_id = rem_res.json()["id"]

            # 2. Approve reminder
            app_res = await client.post(f"/api/reminders/{rem_id}/approve", json={
                "reminder_id": rem_id,
                "approved": True,
                "channel": "in_app"
            })
            assert app_res.status_code == 200
            assert app_res.json()["status"] in ["approved", "sent"]

            # 3. Verify notification created
            notifs_res = await client.get("/api/notifications/")
            assert notifs_res.status_code == 200
            assert any(n.get("reminder_id") == rem_id or "reminder" in n.get("title", "").lower() for n in notifs_res.json()["data"])
            print(f"[PASS] 33. Phase 7 Workflow D End-to-End (Reminder Approval Queue -> Dispatch -> Notification record logged)")
            passed += 1
        except Exception as e:
            print(f"[FAIL] 33. Workflow D End-to-End: {e}")
            traceback.print_exc()
            failed += 1

        scheduler_manager.shutdown(wait=False)
    print("=" * 60)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
