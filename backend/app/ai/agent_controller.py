"""
Agent Controller Module for PayPilot AI (Phase 5).
Coordinates tool selection, input validation, permission checking,
mandatory user confirmation for sensitive operations (PayPal orders),
multi-step workflows, and structured response formatting.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import re

from app.core.config import settings
from app.database import db_manager
from app.ai.llm_service import LLMService
from app.ai.context_manager import ContextManager
from app.ai.conversation_manager import ConversationManager
from app.ai.intent_classifier import IntentClassifier
from app.ai.entity_extractor import EntityExtractor
from app.ai.response_formatter import ResponseFormatter
from app.ai.tools.registry import ToolRegistry
from app.models.schemas import (
    AIChatResponse,
    ExtractedEntities,
    ToolCallResult,
    ActionConfirmation,
)

logger = logging.getLogger("paypilot.ai.agent_controller")

AFFIRMATIVE_RESPONSES = {
    "yes", "confirm", "proceed", "sure", "please do", "generate it",
    "create it", "ok", "okay", "yep", "do it", "approved", "go ahead",
    "generate payment link", "confirm action", "yes please",
}

NEGATIVE_RESPONSES = {
    "no", "cancel", "don't", "stop", "abort", "nevermind", "reject",
    "don't do it", "cancel action", "no thanks",
}

class AgentController:
    """Central orchestrator for PayPilot AI Autonomous Agent with Tool Calling."""

    @classmethod
    async def process_chat(
        cls,
        message: str,
        conversation_id: Optional[str] = None,
        confirmed_action: Optional[Dict[str, Any]] = None,
    ) -> AIChatResponse:
        """
        Processes an incoming user message through the AI Agent Tool Calling Pipeline:
        1. User Confirmation Check: Check for pending sensitive action execution or cancellation.
        2. Intent & Entity Extraction: Understand goal and validate parameters.
        3. Multi-Step & Tool Selection: Execute appropriate backend tools sequentially.
        4. User Confirmation Gate: Request confirmation before creating PayPal orders.
        5. Verification & Response Formatting: Return grounded natural language with rich widgets.
        """
        # 1. Resolve conversation session
        conv_id = await ConversationManager.get_or_create_conversation(conversation_id)
        msg_clean = message.strip()
        msg_lower = msg_clean.lower()

        # 2. Check for Pending Confirmation or Confirmed Action Payload
        pending = await ConversationManager.get_pending_action(conv_id)
        action_payload = confirmed_action or pending

        # Handle explicit cancellation
        if pending and any(neg in msg_lower for neg in NEGATIVE_RESPONSES):
            await ConversationManager.clear_pending_action(conv_id)
            await ConversationManager.add_turn(conv_id, "user", message)
            reply = "Understood. The action has been cancelled without executing."
            await ConversationManager.add_turn(conv_id, "assistant", reply)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent="GENERAL_FINANCIAL_QUERY",
                entities={},
            )

        # Handle affirmative confirmation of pending action
        if action_payload and (confirmed_action or any(aff in msg_lower for aff in AFFIRMATIVE_RESPONSES)):
            action_name = action_payload.get("action")
            await ConversationManager.clear_pending_action(conv_id)
            await ConversationManager.add_turn(conv_id, "user", message)

            if action_name == "create_paypal_order":
                inv_id = action_payload.get("invoice_id")
                inv_no = action_payload.get("invoice_number", inv_id)
                tool_res = await ToolRegistry.execute_tool("create_paypal_order", {"invoice_id": inv_id})

                tools_run = [ToolCallResult(**tool_res)]
                if tool_res["success"]:
                    res_data = tool_res["result"]
                    order_id = res_data["order_id"]
                    approval_url = res_data.get("approval_url") or f"https://www.sandbox.paypal.com/checkoutnow?token={order_id}"
                    amt = res_data["amount"]
                    curr = res_data["currency"]

                    reply = (
                        f"✅ **PayPal Sandbox Payment Link Generated** for invoice **{inv_no}**!\n\n"
                        f"• **PayPal Order ID**: `{order_id}`\n"
                        f"• **Amount**: {curr} {amt:,.2f}\n"
                        f"• **Status**: {res_data['status']}\n\n"
                        f"The client can approve and complete payment using the official PayPal checkout link below."
                    )
                    data_preview = {
                        "type": "paypal_link",
                        "order_id": order_id,
                        "approval_url": approval_url,
                        "invoice_id": inv_id,
                        "invoice_number": inv_no,
                        "amount": amt,
                        "currency": curr,
                    }
                    action_completed = {
                        "action": "create_paypal_order",
                        "order_id": order_id,
                        "approval_url": approval_url,
                        "invoice_number": inv_no,
                        "amount": amt,
                    }
                else:
                    reply = f"❌ Failed to generate PayPal order: {tool_res['error']}"
                    data_preview = None
                    action_completed = None

                await ConversationManager.add_turn(conv_id, "assistant", reply, "CREATE_PAYPAL_ORDER")
                return cls._build_response(
                    conversation_id=conv_id,
                    response=reply,
                    intent="CREATE_PAYPAL_ORDER",
                    entities={},
                    tools_executed=tools_run,
                    data_preview=data_preview,
                    action_completed=action_completed,
                )

            elif action_name == "send_approved_reminder":
                rem_id = action_payload.get("reminder_id")
                channel = action_payload.get("channel", "in_app")
                tool_res = await ToolRegistry.execute_tool("send_approved_reminder", {"reminder_id": rem_id, "channel": channel})
                tools_run = [ToolCallResult(**tool_res)]
                if tool_res["success"]:
                    res_data = tool_res["result"]
                    reply = (
                        f"✅ **Payment Reminder Dispatched Successfully!**\n\n"
                        f"• **Reminder ID**: `{rem_id}`\n"
                        f"• **Channel**: {channel}\n"
                        f"• **Status**: Sent & Delivered\n\n"
                        f"The notification event has been recorded in the audit trail."
                    )
                    data_preview = {"type": "reminder_sent", "reminder": res_data.get("reminder")}
                    action_completed = {"action": "send_approved_reminder", "reminder_id": rem_id}
                else:
                    reply = f"❌ Failed to dispatch reminder: {tool_res.get('error')}"
                    data_preview = None
                    action_completed = None

                await ConversationManager.add_turn(conv_id, "assistant", reply, "SEND_REMINDER")
                return cls._build_response(
                    conversation_id=conv_id,
                    response=reply,
                    intent="SEND_REMINDER",
                    entities={},
                    tools_executed=tools_run,
                    data_preview=data_preview,
                    action_completed=action_completed,
                )

        # 3. Normal incoming turn: Record user turn
        await ConversationManager.add_turn(conv_id, "user", message)

        # 4. Extract Intent and Entities
        intent, _ = IntentClassifier.classify(message)
        entities = EntityExtractor.extract_all(message)
        missing_entities, clarification_needed = EntityExtractor.evaluate_missing_entities(intent, entities)

        tools_executed: List[ToolCallResult] = []
        confirmation_required: Optional[ActionConfirmation] = None
        action_completed: Optional[Dict[str, Any]] = None
        data_preview: Optional[Dict[str, Any]] = None

        # -------------------------------------------------------------
        # Determine Primary Intent / Route
        # -------------------------------------------------------------
        has_payment_link_mention = any(w in msg_lower for w in ["payment link", "paypal link", "pay link", "generate payment", "generate paypal"])
        has_create_invoice_mention = any(w in msg_lower for w in ["create invoice", "create an invoice", "generate an invoice", "new invoice", "make an invoice", "raise an invoice", "bill client", "draft invoice", "bill for"])

        # -------------------------------------------------------------
        # Workflow 1: Direct PayPal Payment Link Request for Existing Invoice
        # -------------------------------------------------------------
        if has_payment_link_mention and not has_create_invoice_mention:
            # Find the target invoice
            target_inv = None
            inv_id = entities.get("invoice_id")
            client_name = entities.get("customer_name")

            if inv_id:
                get_res = await ToolRegistry.execute_tool("get_invoice", {"invoice_id": inv_id})
                tools_executed.append(ToolCallResult(**get_res))
                if get_res["success"] and get_res["result"].get("found"):
                    target_inv = get_res["result"]

            if not target_inv and client_name:
                list_res = await ToolRegistry.execute_tool("list_invoices", {"search": client_name, "status": "pending"})
                tools_executed.append(ToolCallResult(**list_res))
                if list_res["success"] and list_res["result"].get("invoices"):
                    target_inv = list_res["result"]["invoices"][0]

            # If still not found, check search query from raw message
            if not target_inv:
                # e.g. "for Rahul's invoice"
                name_match = re.search(r"(?:for|to)\s+([A-Za-z]+)(?:'s)?", message, re.IGNORECASE)
                if name_match:
                    search_term = name_match.group(1)
                    search_res = await ToolRegistry.execute_tool("list_invoices", {"search": search_term, "status": "pending"})
                    tools_executed.append(ToolCallResult(**search_res))
                    if search_res["success"] and search_res["result"].get("invoices"):
                        target_inv = search_res["result"]["invoices"][0]

            if target_inv:
                inv_no = target_inv.get("invoice_number", target_inv.get("invoice_id"))
                cname = target_inv.get("customer_name", "the customer")
                amt = target_inv.get("total_amount", 0.0)
                curr = target_inv.get("currency", "INR")

                # Store pending action requiring user confirmation
                pending_action = {
                    "action": "create_paypal_order",
                    "invoice_id": target_inv["invoice_id"],
                    "invoice_number": inv_no,
                    "amount": amt,
                    "currency": curr,
                    "customer_name": cname,
                }
                await ConversationManager.set_pending_action(conv_id, pending_action)

                confirmation_required = ActionConfirmation(
                    action="create_paypal_order",
                    description=f"Generate PayPal Sandbox payment link for {cname} ({curr} {amt:,.2f})",
                    parameters={"invoice_id": target_inv["invoice_id"]},
                    requires_confirmation=True,
                )
                data_preview = {
                    "type": "confirmation_card",
                    "action": "create_paypal_order",
                    "invoice_id": target_inv["invoice_id"],
                    "invoice_number": inv_no,
                    "customer_name": cname,
                    "amount": amt,
                    "currency": curr,
                }
                reply = (
                    f"I found invoice **{inv_no}** for **{cname}** totaling **{curr} {amt:,.2f}**.\n\n"
                    f"Shall I generate the PayPal payment link?"
                )
                await ConversationManager.add_turn(conv_id, "assistant", reply, "CREATE_PAYPAL_ORDER")
                return cls._build_response(
                    conversation_id=conv_id,
                    response=reply,
                    intent="CREATE_PAYPAL_ORDER",
                    entities=entities,
                    tools_executed=tools_executed,
                    confirmation_required=confirmation_required,
                    data_preview=data_preview,
                )
            else:
                reply = (
                    "I could not find an unpaid invoice matching your request. "
                    "Please provide the invoice number (e.g. `INV-2026-0001`) or customer name."
                )
                await ConversationManager.add_turn(conv_id, "assistant", reply, "CREATE_PAYPAL_ORDER")
                return cls._build_response(
                    conversation_id=conv_id,
                    response=reply,
                    intent="CREATE_PAYPAL_ORDER",
                    entities=entities,
                    tools_executed=tools_executed,
                )

        # -------------------------------------------------------------
        # Workflow 2: Create Invoice Tool Execution
        # -------------------------------------------------------------
        if has_create_invoice_mention or (intent == "CREATE_INVOICE" and not has_payment_link_mention):
            if clarification_needed:
                missing_str = ", ".join(missing_entities)
                reply = (
                    f"To create this invoice, I need a few more details: **{missing_str}**.\n\n"
                    f"For example: *\"Create an invoice for ₹15,000 for TechCorp due in 10 days\"*"
                )
                await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
                return cls._build_response(
                    conversation_id=conv_id,
                    response=reply,
                    intent=intent,
                    entities=entities,
                    missing_entities=missing_entities,
                    clarification_needed=True,
                )

            # Execute real create_invoice tool
            inv_args = {
                "customer_name": entities["customer_name"],
                "amount": float(entities["amount"]),
                "description": entities.get("description") or "Professional Services",
                "currency": entities.get("currency") or "INR",
                "due_date": entities.get("due_date"),
                "customer_id": entities.get("customer_id"),
            }
            create_res = await ToolRegistry.execute_tool("create_invoice", inv_args)
            tools_executed.append(ToolCallResult(**create_res))

            if create_res["success"]:
                inv = create_res["result"]
                inv_no = inv["invoice_number"]
                cname = inv["customer_name"]
                tot = inv["total_amount"]
                sub = inv["subtotal"]
                tax = inv["tax"]
                curr = inv["currency"]
                due = inv["due_date"]

                action_completed = {
                    "action": "create_invoice",
                    "invoice_id": inv["invoice_id"],
                    "invoice_number": inv_no,
                    "total_amount": tot,
                }
                data_preview = {
                    "type": "invoice_created",
                    "invoice_id": inv["invoice_id"],
                    "invoice_number": inv_no,
                    "customer_name": cname,
                    "subtotal": sub,
                    "tax": tax,
                    "total": tot,
                    "currency": curr,
                    "due_date": due,
                }

                # Multi-Step Check: Did user also ask to generate a payment link?
                if "payment link" in msg_lower or "paypal" in msg_lower or "generate link" in msg_lower:
                    # Require confirmation before generating PayPal link
                    pending_action = {
                        "action": "create_paypal_order",
                        "invoice_id": inv["invoice_id"],
                        "invoice_number": inv_no,
                        "amount": tot,
                        "currency": curr,
                        "customer_name": cname,
                    }
                    await ConversationManager.set_pending_action(conv_id, pending_action)

                    confirmation_required = ActionConfirmation(
                        action="create_paypal_order",
                        description=f"Generate PayPal Sandbox payment link for newly created invoice {inv_no} ({curr} {tot:,.2f})",
                        parameters={"invoice_id": inv["invoice_id"]},
                        requires_confirmation=True,
                    )
                    reply = (
                        f"✅ **Invoice Created Successfully**!\n\n"
                        f"• **Invoice Number**: `{inv_no}`\n"
                        f"• **Client**: {cname}\n"
                        f"• **Subtotal**: {curr} {sub:,.2f}\n"
                        f"• **Tax (18% GST)**: {curr} {tax:,.2f}\n"
                        f"• **Total Amount**: **{curr} {tot:,.2f}**\n"
                        f"• **Due Date**: {due}\n\n"
                        f"Shall I generate the PayPal payment link for this invoice?"
                    )
                else:
                    reply = (
                        f"✅ **Invoice Created Successfully**!\n\n"
                        f"• **Invoice Number**: `{inv_no}`\n"
                        f"• **Client**: {cname}\n"
                        f"• **Subtotal**: {curr} {sub:,.2f}\n"
                        f"• **Tax (18% GST)**: {curr} {tax:,.2f}\n"
                        f"• **Total Amount**: **{curr} {tot:,.2f}**\n"
                        f"• **Due Date**: {due}\n\n"
                        f"This record is saved in MongoDB and is ready for payment tracking."
                    )
            else:
                reply = f"❌ Failed to create invoice: {create_res['error']}"

            await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent=intent,
                entities=entities,
                tools_executed=tools_executed,
                confirmation_required=confirmation_required,
                action_completed=action_completed,
                data_preview=data_preview,
            )

        # -------------------------------------------------------------
        # Phase 6 Specialized Workflows: Prioritize before generic intent match
        # -------------------------------------------------------------
        # Workflow 6B: Upcoming Invoices & Deadlines (Phase 6)
        is_upcoming_query = any(w in msg_lower for w in ["due this week", "invoices due", "upcoming invoices", "due soon", "approaching due", "deadlines"])
        if is_upcoming_query:
            up_res = await ToolRegistry.execute_tool("get_upcoming_invoices", {"days_ahead": 7})
            tools_executed.append(ToolCallResult(**up_res))
            if up_res["success"]:
                res_data = up_res["result"]
                invs = res_data.get("invoices", [])
                cnt = res_data.get("upcoming_count", 0)
                tot = res_data.get("total_due_amount", 0.0)
                lines = [
                    f"• **{i.get('invoice_number', i.get('id'))}** for {i.get('customer_name', i.get('client'))}: ₹{float(i.get('total_amount') or i.get('amount', 0)):,.2f} (Due: {i.get('due_date')})"
                    for i in invs
                ] if invs else ["• No pending invoices approaching due dates in this window."]
                reply = (
                    f"📅 **Upcoming Invoices Due This Week ({cnt} found, totaling ₹{tot:,.2f})**:\n\n"
                    + "\n".join(lines)
                )
                data_preview = {"type": "upcoming_invoices", "count": cnt, "total_due": tot}
            else:
                reply = "Failed to query upcoming invoices."
            await ConversationManager.add_turn(conv_id, "assistant", reply, "CHECK_UPCOMING_INVOICES")
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent="CHECK_UPCOMING_INVOICES",
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # Workflow 6C: Anomaly Detection & Late Payment Analysis (Phase 6)
        is_anomaly_query = any(w in msg_lower for w in ["repeated late payments", "late payments", "anomalies", "anomaly", "unusual transaction", "payment pattern", "repeated late"])
        if is_anomaly_query:
            anom_res = await ToolRegistry.execute_tool("detect_anomalies", {})
            tools_executed.append(ToolCallResult(**anom_res))
            if anom_res["success"]:
                res_data = anom_res["result"]
                anoms = res_data.get("anomalies", [])
                lines = [
                    f"⚠️ **{a['title']}**\n  • {a['description']}\n  • *Insight:* {a['explanation']}"
                    for a in anoms
                ] if anoms else ["✅ No financial anomalies detected. Ledgers and transaction patterns are normal."]
                reply = (
                    f"🔍 **Financial Anomaly & Risk Analysis** ({len(anoms)} finding(s)):\n\n"
                    + "\n\n".join(lines)
                    + "\n\n*Note: All findings are statistical alerts and advisory only.*"
                )
                data_preview = {"type": "anomalies_list", "count": len(anoms)}
            else:
                reply = "Error analyzing financial anomalies."
            await ConversationManager.add_turn(conv_id, "assistant", reply, "DETECT_ANOMALIES")
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent="DETECT_ANOMALIES",
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # Workflow 6D: Batch Overdue Reminders & Send Reminders (Phase 6)
        is_batch_remind_query = any(w in msg_lower for w in ["remind customers whose invoices are overdue", "prepare reminders for all overdue", "remind overdue customers", "prepare overdue reminders"])
        if is_batch_remind_query:
            batch_res = await ToolRegistry.execute_tool("prepare_overdue_reminders", {"tone": "professional"})
            tools_executed.append(ToolCallResult(**batch_res))
            if batch_res["success"]:
                res_data = batch_res["result"]
                rems = res_data.get("reminders", [])
                lines = [
                    f"• **{r.get('customer_name')}** ({r.get('invoice_id')}): \"{r.get('message')[:90]}...\""
                    for r in rems
                ] if rems else ["• No overdue invoices requiring new reminders (duplicates within 3 days prevented)."]
                reply = (
                    f"🔔 **Prepared {len(rems)} Personalized Reminder(s) for Overdue Accounts**:\n\n"
                    + "\n".join(lines)
                    + "\n\nAll generated reminders are saved in **Pending Approval** state in your Reminders registry for review."
                )
                data_preview = {"type": "batch_reminders_prepared", "count": len(rems)}
            else:
                reply = "Error preparing overdue reminders."
            await ConversationManager.add_turn(conv_id, "assistant", reply, "PREPARE_REMINDERS")
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent="PREPARE_REMINDERS",
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        is_send_rem_query = any(w in msg_lower for w in ["send reminder", "dispatch reminder", "approve reminder"])
        if is_send_rem_query:
            rem_id_match = re.search(r"(rem_[a-f0-9]+)", message)
            target_rem_id = rem_id_match.group(1) if rem_id_match else None
            if not target_rem_id:
                pending_rem = await db_manager.reminders.find_one({"approval_status": "pending"})
                if pending_rem:
                    target_rem_id = pending_rem.get("id")

            if target_rem_id:
                rem_doc = await db_manager.reminders.find_one({"id": target_rem_id})
                c_name = rem_doc.get("customer_name", "the customer") if rem_doc else "the customer"
                pending_action = {
                    "action": "send_approved_reminder",
                    "reminder_id": target_rem_id,
                    "customer_name": c_name,
                    "channel": "in_app",
                }
                await ConversationManager.set_pending_action(conv_id, pending_action)
                confirmation_required = ActionConfirmation(
                    action="send_approved_reminder",
                    description=f"Send payment reminder {target_rem_id} to {c_name}",
                    parameters={"reminder_id": target_rem_id},
                    requires_confirmation=True,
                )
                reply = (
                    f"I found pending reminder **{target_rem_id}** for **{c_name}**.\n\n"
                    f"Shall I dispatch this payment reminder notification to the customer?"
                )
                data_preview = {"type": "confirmation_card", "action": "send_approved_reminder", "reminder_id": target_rem_id}
                await ConversationManager.add_turn(conv_id, "assistant", reply, "SEND_REMINDER")
                return cls._build_response(
                    conversation_id=conv_id,
                    response=reply,
                    intent="SEND_REMINDER",
                    entities=entities,
                    tools_executed=tools_executed,
                    confirmation_required=confirmation_required,
                    data_preview=data_preview,
                )

        # -------------------------------------------------------------
        # Workflow 3: Multi-Step Overdue Invoices & Reminders
        # -------------------------------------------------------------
        if intent == "CHECK_OVERDUE_INVOICES" or (intent == "GENERATE_REMINDER" and "overdue" in msg_lower):
            overdue_res = await ToolRegistry.execute_tool("find_overdue_invoices", {"limit": 10})
            tools_executed.append(ToolCallResult(**overdue_res))
            overdue_data = overdue_res.get("result", {})
            invoices = overdue_data.get("overdue_invoices", [])
            total_amt = overdue_data.get("total_overdue_amount", 0.0)

            if not invoices:
                reply = "🎉 Great news! You have **no overdue invoices** currently."
                data_preview = None
            else:
                # Multi-Step: Prepare draft reminders for overdue clients
                reminders_preview = []
                for inv in invoices[:3]:
                    rem_res = await ToolRegistry.execute_tool("generate_payment_reminder", {"invoice_id": inv["invoice_id"]})
                    tools_executed.append(ToolCallResult(**rem_res))
                    if rem_res["success"]:
                        reminders_preview.append(rem_res["result"])

                lines = [
                    f"• **{i['invoice_number']}** ({i['customer_name']}): ₹{i['total_amount']:,.2f} (Due: {i['due_date']})"
                    for i in invoices
                ]
                rem_lines = [
                    f"> *\"{r['draft_message']}\"*"
                    for r in reminders_preview
                ]

                reply = (
                    f"⚠️ Found **{len(invoices)} overdue invoice(s)** totaling **₹{total_amt:,.2f}**:\n\n"
                    + "\n".join(lines)
                    + "\n\n📝 **Prepared Reminder Drafts**:\n"
                    + "\n\n".join(rem_lines)
                    + "\n\nWould you like me to schedule these reminders in the Reminders registry?"
                )
                data_preview = {
                    "type": "overdue_list",
                    "count": len(invoices),
                    "total": total_amt,
                }

            await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent=intent,
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # -------------------------------------------------------------
        # Workflow 4: Single Reminder Scheduling
        # -------------------------------------------------------------
        if intent == "GENERATE_REMINDER":
            target = entities.get("invoice_id") or entities.get("customer_name")
            if target:
                gen_res = await ToolRegistry.execute_tool("generate_payment_reminder", {"invoice_id": target})
                tools_executed.append(ToolCallResult(**gen_res))
                if gen_res["success"]:
                    rem_data = gen_res["result"]
                    # Schedule reminder in database
                    sched_res = await ToolRegistry.execute_tool("create_reminder", {
                        "invoice_id": rem_data["invoice_id"],
                        "message": rem_data["draft_message"],
                    })
                    tools_executed.append(ToolCallResult(**sched_res))

                    reply = (
                        f"🔔 **Payment Reminder Scheduled** for **{rem_data['customer_name']}** "
                        f"(Invoice: {rem_data['invoice_number']})!\n\n"
                        f"> *\"{rem_data['draft_message']}\"*\n\n"
                        f"The reminder has been queued in your Reminders registry."
                    )
                    action_completed = {"action": "create_reminder", "invoice_id": rem_data["invoice_id"]}
                else:
                    reply = f"Could not locate an open invoice for '{target}' to generate a reminder."
            else:
                reply = "Please specify the invoice number or client name you want to generate a reminder for."

            await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent=intent,
                entities=entities,
                tools_executed=tools_executed,
                action_completed=action_completed,
            )

        # -------------------------------------------------------------
        # Workflow 5: Multi-Step Customer Search & Unpaid Invoices
        # -------------------------------------------------------------
        is_customer_lookup = (
            any(w in msg_lower for w in ["find customer", "lookup customer", "search customer", "customer details"])
            and not any(w in msg_lower for w in ["late payment", "anomal", "repeated late"])
        )
        if is_customer_lookup or (entities.get("customer_name") and intent == "CHECK_PENDING_PAYMENTS"):
            cname = entities.get("customer_name") or msg_clean
            search_res = await ToolRegistry.execute_tool("search_customer", {"query": cname})
            tools_executed.append(ToolCallResult(**search_res))

            if search_res["success"] and search_res["result"].get("found"):
                cust = search_res["result"]["customers"][0]
                # Multi-Step: Get their invoices
                invs_res = await ToolRegistry.execute_tool("list_invoices", {"customer_id": cust["customer_id"]})
                tools_executed.append(ToolCallResult(**invs_res))
                cust_invs = invs_res.get("result", {}).get("invoices", [])

                lines = [
                    f"• **{i['invoice_number']}**: ₹{i['total_amount']:,.2f} ({i['status']})"
                    for i in cust_invs
                ] if cust_invs else ["• No invoices found for this customer."]

                reply = (
                    f"👤 **Customer Profile**: **{cust['name']}**\n\n"
                    f"• **Email**: {cust.get('email', 'N/A')}\n"
                    f"• **Company**: {cust.get('company', 'N/A')}\n\n"
                    f"📄 **Associated Invoices**:\n"
                    + "\n".join(lines)
                )
                data_preview = {"type": "customer_card", "customer": cust, "invoices": cust_invs}
            else:
                reply = f"No customer record found matching '{cname}' in your database."

            await ConversationManager.add_turn(conv_id, "assistant", reply, "CUSTOMER_LOOKUP")
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent="CUSTOMER_LOOKUP",
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # -------------------------------------------------------------
        # Workflow 6: Revenue Analytics & Financial Intelligence (Phase 6)
        # -------------------------------------------------------------
        is_deep_fin_query = any(w in msg_lower for w in ["summarize my revenue this month", "explain why revenue decreased", "revenue forecast", "forecast", "financial intelligence", "mom"])
        if intent == "ANALYZE_REVENUE" or is_deep_fin_query:
            fin_res = await ToolRegistry.execute_tool("get_financial_analysis", {"include_forecast": True})
            tools_executed.append(ToolCallResult(**fin_res))

            if fin_res["success"]:
                f_data = fin_res["result"]
                mom = f_data.get("mom_comparison", {})
                forecast = f_data.get("forecast", {})
                m_rev = f_data.get("monthly_revenue", 0.0)
                pend = f_data.get("outstanding_amount", 0.0)
                overdue = f_data.get("overdue_amount", 0.0)

                reply = (
                    f"📊 **Financial Intelligence & Revenue Summary**:\n\n"
                    f"• **Current Month Revenue**: ₹{m_rev:,.2f}\n"
                    f"• **Outstanding Receivables**: ₹{pend:,.2f} (Overdue: ₹{overdue:,.2f})\n"
                    f"• **Month-over-Month Comparison**: {mom.get('growth_rate_pct', 0)}% ({mom.get('trend_direction', 'flat')})\n"
                    f"  *{mom.get('explanation', '')}*\n\n"
                    f"🔮 **Revenue Forecast ({forecast.get('target_period', 'Next Month')})**: "
                    f"**₹{forecast.get('forecast_amount', 0):,.2f}** *(Estimated)*\n"
                    f"  *{forecast.get('disclaimer', '')}*\n\n"
                    f"All metrics are calculated strictly from verified database records."
                )
                data_preview = {
                    "type": "financial_intelligence",
                    "monthly_revenue": m_rev,
                    "mom_comparison": mom,
                    "forecast": forecast,
                }
            else:
                reply = f"Error computing financial analysis: {fin_res['error']}"

            await ConversationManager.add_turn(conv_id, "assistant", reply, "ANALYZE_REVENUE")
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent="ANALYZE_REVENUE",
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # -------------------------------------------------------------
        # Workflow 7: Payment Status Lookup
        # -------------------------------------------------------------
        if intent == "PAYMENT_STATUS":
            inv_ref = entities.get("invoice_id")
            if inv_ref:
                status_res = await ToolRegistry.execute_tool("get_payment_status", {"invoice_id": inv_ref})
                tools_executed.append(ToolCallResult(**status_res))
                if status_res["success"] and status_res["result"].get("found"):
                    st_data = status_res["result"]
                    reply = (
                        f"Payment status for invoice **{st_data.get('invoice_number', inv_ref)}**:\n\n"
                        f"• **Status**: **{st_data['status'].upper()}**\n"
                        f"• **Amount**: {st_data.get('currency', 'INR')} {st_data.get('amount', 0):,.2f}\n"
                        f"• **Is Paid**: {'Yes' if st_data.get('is_paid') else 'No'}\n"
                        f"• **PayPal Order**: `{st_data.get('paypal_order_id') or 'None'}`"
                    )
                else:
                    reply = f"Invoice '{inv_ref}' not found in the payment registry."
            else:
                reply = "Please specify the invoice ID (e.g. `INV-2026-0001`) to check its payment status."

            await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent=intent,
                entities=entities,
                tools_executed=tools_executed,
            )

        # -------------------------------------------------------------
        # Workflow 8: Transactions History
        # -------------------------------------------------------------
        if intent == "VIEW_TRANSACTIONS":
            txn_res = await ToolRegistry.execute_tool("get_transaction_history", {"limit": 5})
            tools_executed.append(ToolCallResult(**txn_res))
            if txn_res["success"]:
                txns = txn_res["result"].get("transactions", [])
                lines = [
                    f"• **{t['transaction_id']}**: {t['currency']} {t['amount']:,.2f} | Status: **{t['status']}** | Method: {t.get('payment_method', 'PayPal')} | Date: {t['date']}"
                    for t in txns
                ]
                reply = f"💳 **Verified Transaction Ledger**:\n\n" + "\n".join(lines)
                data_preview = {"type": "transaction_list", "count": len(txns)}
            else:
                reply = "Failed to retrieve transaction history."

            await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent=intent,
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # -------------------------------------------------------------
        # Workflow 9: Pending Invoices
        # -------------------------------------------------------------
        if intent == "CHECK_PENDING_PAYMENTS":
            pend_res = await ToolRegistry.execute_tool("get_pending_payments", {})
            tools_executed.append(ToolCallResult(**pend_res))
            if pend_res["success"]:
                p_data = pend_res["result"]
                unpaid = p_data.get("unpaid_invoices", [])
                tot = p_data.get("total_pending_amount", 0.0)

                lines = [
                    f"• **{i['invoice_number']}** ({i['customer_name']}): ₹{i['total_amount']:,.2f} (Status: {i['status']}, Due: {i['due_date']})"
                    for i in unpaid[:5]
                ]
                reply = (
                    f"Found **{p_data['count']} pending payment(s)** totaling **₹{tot:,.2f}**:\n\n"
                    + "\n".join(lines)
                    + "\n\nYou can ask me to generate a payment link or send reminders for any of these."
                )
                data_preview = {"type": "pending_summary", "count": p_data["count"], "total": tot}
            else:
                reply = "Could not retrieve pending payments."

            await ConversationManager.add_turn(conv_id, "assistant", reply, intent)
            return cls._build_response(
                conversation_id=conv_id,
                response=reply,
                intent=intent,
                entities=entities,
                tools_executed=tools_executed,
                data_preview=data_preview,
            )

        # -------------------------------------------------------------
        # Default / General Query Handling
        # -------------------------------------------------------------
        grounding_data = await ContextManager.get_system_grounding_context()
        raw_res = await LLMService.generate_structured_response(
            user_message=message,
            grounding_data=grounding_data,
            conversation_history=await ConversationManager.get_history(conv_id, limit=6),
        )
        formatted = ResponseFormatter.format_and_guard(raw_res, grounding_data)
        await ConversationManager.add_turn(conv_id, "assistant", formatted["response"], formatted["intent"])

        return cls._build_response(
            conversation_id=conv_id,
            response=formatted["response"],
            intent=formatted["intent"],
            entities=formatted.get("entities", entities),
            missing_entities=formatted.get("missing_entities", []),
            clarification_needed=formatted.get("clarification_needed", False),
            data_preview=formatted.get("data_preview"),
        )

    @classmethod
    def _build_response(
        cls,
        conversation_id: str,
        response: str,
        intent: str,
        entities: Dict[str, Any],
        tools_executed: Optional[List[ToolCallResult]] = None,
        confirmation_required: Optional[ActionConfirmation] = None,
        action_completed: Optional[Dict[str, Any]] = None,
        data_preview: Optional[Dict[str, Any]] = None,
        missing_entities: Optional[List[str]] = None,
        clarification_needed: bool = False,
    ) -> AIChatResponse:
        """Helper to construct standard AIChatResponse."""
        now_iso = datetime.utcnow().isoformat()
        active_model = f"{settings.ai_provider}:{settings.ai_model}" if LLMService.is_api_key_configured() else "paypilot-autonomous-agent:tools"

        # Safe conversion of entities dict to ExtractedEntities
        clean_entities = entities if isinstance(entities, dict) else {}
        entities_model = ExtractedEntities(**{k: v for k, v in clean_entities.items() if k in ExtractedEntities.model_fields})

        return AIChatResponse(
            conversation_id=conversation_id,
            response=response,
            intent=intent,
            entities=entities_model,
            missing_entities=missing_entities or [],
            clarification_needed=clarification_needed,
            tools_executed=tools_executed or [],
            confirmation_required=confirmation_required,
            action_completed=action_completed,
            data_preview=data_preview,
            timestamp=now_iso,
            model_used=active_model,
            grounded=True,
        )
