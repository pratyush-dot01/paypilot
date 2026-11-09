"""
Response Formatter Module for PayPilot AI (Phase 4).
Applies financial formatting, markdown styling, rich UI preview payloads,
and safety/guardrail checks.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("paypilot.ai.response_formatter")

FORBIDDEN_PHRASES = [
    "payment has been executed",
    "i have charged the customer",
    "payment successfully captured without user",
    "your card has been billed",
]

class ResponseFormatter:
    """Formats AI responses and enforces safety and formatting guardrails."""

    @classmethod
    def format_and_guard(
        cls,
        raw_response: Dict[str, Any],
        grounding_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Enforce safety guardrails and format payload.
        """
        response_text = raw_response.get("response", "")
        intent = raw_response.get("intent", "GENERAL_FINANCIAL_QUERY")
        entities = raw_response.get("entities", {})
        data_preview = raw_response.get("data_preview")

        # 1. Safety Guardrail: Block unauthorized automatic payment claims
        for phrase in FORBIDDEN_PHRASES:
            if phrase in response_text.lower():
                logger.warning(f"Guardrail triggered for unauthorized payment phrasing: {phrase}")
                response_text = (
                    "⚠️ Notice: Payment execution requires human confirmation through PayPal. "
                    "In PayPilot Phase 4, AI can only inspect, summarize, and draft financial records."
                )
                data_preview = None

        # 2. Safety Guardrail: Mask any inadvertent token or key leakage
        if "sk-" in response_text or "access_token" in response_text:
            response_text = "Security check: API credentials cannot be displayed."

        # 3. Enhance data preview for UI rendering
        if intent == "CREATE_INVOICE" and not raw_response.get("clarification_needed"):
            if not data_preview and entities.get("amount"):
                amt = float(entities["amount"])
                tax = round(amt * 0.18, 2)
                data_preview = {
                    "type": "invoice_draft",
                    "customer_name": entities.get("customer_name") or "New Client",
                    "subtotal": amt,
                    "tax": tax,
                    "total": round(amt + tax, 2),
                    "currency": entities.get("currency") or "INR",
                    "due_date": entities.get("due_date") or "Due on Receipt",
                    "description": entities.get("description") or "Professional Services",
                }

        return {
            "response": response_text,
            "intent": intent,
            "entities": entities,
            "missing_entities": raw_response.get("missing_entities", []),
            "clarification_needed": raw_response.get("clarification_needed", False),
            "data_preview": data_preview,
        }

