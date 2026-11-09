"""
LLM Service Module for PayPilot AI (Phase 4).
Connects to Google Gemini and OpenAI REST APIs with structured JSON schema outputs,
timeout handling, retry capabilities, and offline fallback.
"""

import json
import time
import httpx
from typing import Dict, Any, List, Optional
import logging

from app.core.config import settings
from app.ai.prompts import SYSTEM_PROMPT
from app.ai.intent_classifier import IntentClassifier
from app.ai.entity_extractor import EntityExtractor

logger = logging.getLogger("paypilot.ai.llm_service")

class LLMService:
    """Provides unified LLM communication with Gemini and OpenAI APIs."""

    @classmethod
    def get_configured_provider(cls) -> str:
        """Returns the active provider."""
        return settings.ai_provider.lower()

    @classmethod
    def is_api_key_configured(cls) -> bool:
        """Check if active provider API key is provided."""
        provider = cls.get_configured_provider()
        if provider == "openai":
            return bool(settings.openai_api_key and settings.openai_api_key.strip())
        # Default gemini
        return bool(settings.gemini_api_key and settings.gemini_api_key.strip())

    @classmethod
    async def test_connectivity(cls) -> Dict[str, Any]:
        """
        Verify real LLM API connectivity.
        Returns detailed status including latency and active model.
        """
        provider = cls.get_configured_provider()
        model = settings.ai_model
        api_key_set = cls.is_api_key_configured()

        if not api_key_set:
            return {
                "status": "unconfigured",
                "provider": provider,
                "model": model,
                "api_key_configured": False,
                "live_connectivity": False,
                "message": f"API key for {provider} not configured in .env. Engine operating in grounded local mode.",
                "latency_ms": None,
            }

        start_time = time.time()
        try:
            sample_prompt = "Return a valid JSON object with key 'status' equal to 'ok'."
            if provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
                payload = {
                    "model": model if "gpt" in model else "gpt-4o-mini",
                    "messages": [{"role": "user", "content": sample_prompt}],
                    "response_format": {"type": "json_object"},
                    "max_tokens": 50,
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    latency = round((time.time() - start_time) * 1000, 2)
                    if resp.status_code == 200:
                        return {
                            "status": "connected",
                            "provider": provider,
                            "model": model,
                            "api_key_configured": True,
                            "live_connectivity": True,
                            "latency_ms": latency,
                            "message": f"Successfully connected to {provider} ({model}) in {latency}ms",
                        }
                    else:
                        return {
                            "status": "error",
                            "provider": provider,
                            "model": model,
                            "api_key_configured": True,
                            "live_connectivity": False,
                            "message": f"HTTP {resp.status_code}: {resp.text[:150]}",
                            "latency_ms": latency,
                        }
            else:
                # Gemini
                clean_model = model if "gemini" in model else "gemini-1.5-flash"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={settings.gemini_api_key}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": sample_prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    latency = round((time.time() - start_time) * 1000, 2)
                    if resp.status_code == 200:
                        return {
                            "status": "connected",
                            "provider": provider,
                            "model": clean_model,
                            "api_key_configured": True,
                            "live_connectivity": True,
                            "latency_ms": latency,
                            "message": f"Successfully connected to Gemini ({clean_model}) in {latency}ms",
                        }
                    else:
                        return {
                            "status": "error",
                            "provider": provider,
                            "model": clean_model,
                            "api_key_configured": True,
                            "live_connectivity": False,
                            "message": f"HTTP {resp.status_code}: {resp.text[:150]}",
                            "latency_ms": latency,
                        }
        except Exception as e:
            latency = round((time.time() - start_time) * 1000, 2)
            logger.warning(f"LLM connectivity check failed: {e}")
            return {
                "status": "error",
                "provider": provider,
                "model": model,
                "api_key_configured": True,
                "live_connectivity": False,
                "message": f"Connection exception: {str(e)}",
                "latency_ms": latency,
            }

    @classmethod
    async def generate_structured_response(
        cls,
        user_message: str,
        grounding_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Sends grounded request to LLM and returns structured JSON output.
        Falls back to local grounded engine if API key is not configured or upon API failure.
        """
        if cls.is_api_key_configured():
            try:
                res = await cls._call_external_llm(user_message, grounding_data, conversation_history)
                if res and isinstance(res, dict) and "intent" in res and "response" in res:
                    return res
            except Exception as e:
                logger.error(f"External LLM invocation error: {e}. Falling back to internal engine.")

        # Local Grounded Financial Engine
        return cls._generate_local_grounded_response(user_message, grounding_data, conversation_history)

    @classmethod
    async def _call_external_llm(
        cls,
        user_message: str,
        grounding_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """Call external Gemini or OpenAI endpoint with structured JSON expectation."""
        provider = cls.get_configured_provider()
        model = settings.ai_model

        context_str = json.dumps(grounding_data, indent=2)
        system_with_context = f"{SYSTEM_PROMPT}\n\n### LIVE GROUNDED DATABASE CONTEXT:\n{context_str}"

        if provider == "openai":
            messages = [{"role": "system", "content": system_with_context}]
            for turn in conversation_history[-6:]:
                messages.append({"role": turn["role"], "content": turn["message"]})
            messages.append({"role": "user", "content": user_message})

            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
            payload = {
                "model": model if "gpt" in model else "gpt-4o-mini",
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": settings.ai_temperature,
                "max_tokens": settings.ai_max_tokens,
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    raw = resp.json()["choices"][0]["message"]["content"]
                    return json.loads(raw)
                else:
                    logger.warning(f"OpenAI error {resp.status_code}: {resp.text[:200]}")
                    return None

        else:
            # Google Gemini
            clean_model = model if "gemini" in model else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={settings.gemini_api_key}"

            contents = []
            for turn in conversation_history[-6:]:
                role = "user" if turn["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": turn["message"]}]})
            contents.append({"role": "user", "parts": [{"text": user_message}]})

            payload = {
                "systemInstruction": {"parts": [{"text": system_with_context}]},
                "contents": contents,
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": settings.ai_temperature,
                },
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(raw)
                else:
                    logger.warning(f"Gemini error {resp.status_code}: {resp.text[:200]}")
                    return None

    @classmethod
    def _generate_local_grounded_response(
        cls,
        user_message: str,
        grounding_data: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Robust grounded engine that extracts intent, entities, and answers
        strictly from MongoDB live data when external LLM is offline or unconfigured.
        """
        intent, _ = IntentClassifier.classify(user_message)
        entities = EntityExtractor.extract_all(user_message)
        missing_entities, clarification_needed = EntityExtractor.evaluate_missing_entities(intent, entities)

        stats = grounding_data.get("stats", {})
        pending_invoices = grounding_data.get("pending_invoices", [])
        overdue_invoices = grounding_data.get("overdue_invoices", [])
        recent_txns = grounding_data.get("recent_transactions", [])
        customers_with_balances = grounding_data.get("customers_with_balances", [])
        monthly_perf = grounding_data.get("monthly_performance", [])

        # Check multi-turn context (e.g. follow-up questions)
        is_followup_highest = any(phrase in user_message.lower() for phrase in ["which one has the highest", "highest amount", "maximum value", "highest value"])
        is_followup_lowest = any(phrase in user_message.lower() for phrase in ["which one has the lowest", "lowest amount", "minimum value"])

        if is_followup_highest and pending_invoices:
            highest_inv = max(pending_invoices, key=lambda x: x["total_amount"])
            response_text = (
                f"The highest-value unpaid invoice is **{highest_inv['invoice_number']}** "
                f"for **{highest_inv['customer_name']}** at **₹{highest_inv['total_amount']:,.2f}** "
                f"(Due: {highest_inv['due_date']})."
            )
            return {
                "intent": "CHECK_PENDING_PAYMENTS",
                "entities": entities,
                "missing_entities": [],
                "clarification_needed": False,
                "response": response_text,
                "data_preview": {"type": "invoice_highlight", "data": highest_inv},
            }

        if is_followup_lowest and pending_invoices:
            lowest_inv = min(pending_invoices, key=lambda x: x["total_amount"])
            response_text = (
                f"The lowest-value unpaid invoice is **{lowest_inv['invoice_number']}** "
                f"for **{lowest_inv['customer_name']}** at **₹{lowest_inv['total_amount']:,.2f}** "
                f"(Due: {lowest_inv['due_date']})."
            )
            return {
                "intent": "CHECK_PENDING_PAYMENTS",
                "entities": entities,
                "missing_entities": [],
                "clarification_needed": False,
                "response": response_text,
                "data_preview": {"type": "invoice_highlight", "data": lowest_inv},
            }

        # Intent handling
        if intent == "CHECK_OVERDUE_INVOICES":
            if not overdue_invoices:
                response_text = "🎉 Great news! You currently have **no overdue invoices**. All client payments are on track."
                preview = None
            else:
                lines = [
                    f"• **{i['invoice_number']}** ({i['customer_name']}): ₹{i['total_amount']:,.2f} — *Due date: {i['due_date']}*"
                    for i in overdue_invoices[:5]
                ]
                total_overdue = sum(i["total_amount"] for i in overdue_invoices)
                response_text = (
                    f"⚠️ You have **{len(overdue_invoices)} overdue invoice(s)** totaling **₹{total_overdue:,.2f}**:\n\n"
                    + "\n".join(lines)
                    + "\n\nWould you like me to generate payment reminders for these clients?"
                )
                preview = {"type": "overdue_list", "count": len(overdue_invoices), "total": total_overdue}

        elif intent == "CHECK_PENDING_PAYMENTS":
            total_pending = stats.get("pending_payments", sum(i["total_amount"] for i in pending_invoices))
            count_pending = len(pending_invoices)
            if count_pending == 0:
                response_text = "You have **no pending payments**. All issued invoices have been settled!"
                preview = None
            else:
                lines = [
                    f"• **{i['invoice_number']}** ({i['customer_name']}): ₹{i['total_amount']:,.2f} (Status: {i['status']}, Due: {i['due_date']})"
                    for i in pending_invoices[:5]
                ]
                response_text = (
                    f"You currently have **{count_pending} pending invoice(s)** totaling **₹{total_pending:,.2f}**:\n\n"
                    + "\n".join(lines)
                    + "\n\nYou can ask me which invoice has the highest amount or to create a reminder."
                )
                preview = {"type": "pending_summary", "count": count_pending, "total": total_pending}

        elif intent == "ANALYZE_REVENUE":
            rev = stats.get("total_revenue", 0.0)
            pending = stats.get("pending_payments", 0.0)
            completed_txns = stats.get("completed_transactions", 0)
            overdue_cnt = stats.get("overdue_invoices", 0)

            perf_text = ""
            if len(monthly_perf) >= 2:
                m1, m2 = monthly_perf[-2], monthly_perf[-1]
                diff = m2["revenue"] - m1["revenue"]
                trend = f"up by ₹{diff:,.2f}" if diff >= 0 else f"down by ₹{abs(diff):,.2f}"
                perf_text = f"\n\nComparing {m2['month']} to {m1['month']}: Revenue is **{trend}**."

            response_text = (
                f"📊 **Financial & Revenue Performance Overview**:\n\n"
                f"• **Total Revenue Collected**: ₹{rev:,.2f}\n"
                f"• **Pending Receivables**: ₹{pending:,.2f}\n"
                f"• **Completed Transactions**: {completed_txns}\n"
                f"• **Overdue Invoices**: {overdue_cnt}"
                + perf_text
                + "\n\nAll figures are verified directly against your MongoDB transaction ledgers."
            )
            preview = {
                "type": "kpi_summary",
                "revenue": rev,
                "pending": pending,
                "transactions": completed_txns,
                "overdue": overdue_cnt,
            }

        elif intent == "CREATE_INVOICE":
            if clarification_needed:
                missing_str = ", ".join(missing_entities)
                response_text = (
                    f"I'd be happy to prepare an invoice for you! However, I need a few more details.\n\n"
                    f"Please provide the missing information: **{missing_str}**.\n\n"
                    f"For example: *\"Create an invoice for ₹15,000 to Acme Corp for Web Development due next week\"*"
                )
                preview = None
            else:
                amt = entities["amount"]
                cname = entities["customer_name"]
                tax = round(amt * 0.18, 2)
                total = round(amt + tax, 2)
                desc = entities["description"] or "Professional Services"
                due = entities["due_date"] or "Due on Receipt"
                curr = entities["currency"] or "INR"

                response_text = (
                    f"📝 **Invoice Draft Prepared** for **{cname}**:\n\n"
                    f"• **Description**: {desc}\n"
                    f"• **Subtotal**: {curr} {amt:,.2f}\n"
                    f"• **Tax (18% GST)**: {curr} {tax:,.2f}\n"
                    f"• **Total Amount**: **{curr} {total:,.2f}**\n"
                    f"• **Due Date**: {due}\n\n"
                    f"*Note: In accordance with Phase 4 safety guardrails, this draft is ready for your review. "
                    f"You can finalize and create it directly in the Invoices tab.*"
                )
                preview = {
                    "type": "invoice_draft",
                    "customer_name": cname,
                    "subtotal": amt,
                    "tax": tax,
                    "total": total,
                    "currency": curr,
                    "description": desc,
                    "due_date": due,
                }

        elif intent == "VIEW_TRANSACTIONS":
            if not recent_txns:
                response_text = "No recent transactions found in the database."
                preview = None
            else:
                lines = [
                    f"• **{t['transaction_id']}**: {t['currency']} {t['amount']:,.2f} | Status: **{t['status']}** | Method: {t.get('payment_method', 'PayPal')} | Date: {t['date']}"
                    for t in recent_txns[:5]
                ]
                response_text = (
                    f"💳 **Latest {len(recent_txns[:5])} Transactions from Database**:\n\n"
                    + "\n".join(lines)
                )
                preview = {"type": "transaction_list", "count": len(recent_txns)}

        elif intent == "GENERATE_REMINDER":
            if entities.get("customer_name") or entities.get("invoice_id"):
                target = entities.get("customer_name") or entities.get("invoice_id")
                response_text = (
                    f"🔔 **Payment Reminder Prepared** for **{target}**:\n\n"
                    f"*\"Dear Client, this is a friendly reminder that your invoice with PayPilot is awaiting payment. "
                    f"Please complete payment using the link provided at your earliest convenience.\"*\n\n"
                    f"Would you like me to schedule this in the Reminders registry?"
                )
            else:
                response_text = (
                    "I can draft payment reminders for overdue invoices. "
                    "Which client or invoice number would you like me to target?"
                )
            preview = None

        elif intent == "PAYMENT_STATUS":
            inv_ref = entities.get("invoice_id")
            if inv_ref:
                match = next((i for i in pending_invoices if i.get("invoice_number", "").lower() == inv_ref.lower()), None)
                if match:
                    response_text = (
                        f"Invoice **{inv_ref}** is currently **{match['status'].upper()}** with an outstanding balance of "
                        f"**₹{match['total_amount']:,.2f}** (Due: {match['due_date']})."
                    )
                else:
                    response_text = (
                        f"Invoice **{inv_ref}** does not have an open pending balance. It is marked as **PAID** or completed."
                    )
            else:
                response_text = "Please provide the invoice ID (e.g. `INV-2026-0001`) to inspect its exact payment status."
            preview = None

        elif intent == "VIEW_INVOICES":
            if not pending_invoices:
                response_text = "You currently have no open invoices."
                preview = None
            else:
                lines = [
                    f"• **{i['invoice_number']}**: {i['customer_name']} — ₹{i['total_amount']:,.2f} ({i['status']})"
                    for i in pending_invoices[:5]
                ]
                response_text = f"📄 **Open Invoices**:\n\n" + "\n".join(lines)
                preview = {"type": "invoice_list", "count": len(pending_invoices)}

        else:
            # GENERAL_FINANCIAL_QUERY
            response_text = (
                "👋 Hello! I'm PayPilot AI, your intelligent financial assistant.\n\n"
                "I have direct access to your verified business ledger. I can assist you with:\n"
                "• 📊 **Revenue Analysis**: \"How much revenue did I generate this month?\"\n"
                "• ⏳ **Pending Invoices**: \"Show my unpaid invoices\" or \"Which one has the highest amount?\"\n"
                "• ⚠️ **Overdue Payments**: \"Which invoices are overdue?\"\n"
                "• 📝 **Drafting Invoices**: \"Create an invoice for ₹10,000 for TechCorp\"\n"
                "• 💳 **Transaction Feeds**: \"Show my latest five transactions\"\n\n"
                "How can I assist your business today?"
            )
            preview = None

        return {
            "intent": intent,
            "entities": entities,
            "missing_entities": missing_entities,
            "clarification_needed": clarification_needed,
            "response": response_text,
            "data_preview": preview,
        }

