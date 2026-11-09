"""
Entity Extraction Module for PayPilot AI (Phase 4).
Extracts customer names, financial amounts, currencies, due dates, invoice IDs, and transaction IDs.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger("paypilot.ai.entity_extractor")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
INVOICE_ID_REGEX = re.compile(r"(INV-\d{4}-\d{4}|inv_[a-f0-9]{8,24}|#INV-?\d+)", re.IGNORECASE)
TRANSACTION_ID_REGEX = re.compile(r"(txn_[a-f0-9]{8,24}|TXN-\d+|PAYID-[A-Z0-9]+)", re.IGNORECASE)

class EntityExtractor:
    """Extracts financial and business entities from natural language messages."""

    @classmethod
    def extract_all(cls, text: str) -> Dict[str, Any]:
        """Extract all potential entities from text."""
        return {
            "customer_name": cls.extract_customer_name(text),
            "customer_email": cls.extract_email(text),
            "amount": cls.extract_amount(text),
            "currency": cls.extract_currency(text),
            "description": cls.extract_description(text),
            "items": cls.extract_items(text),
            "due_date": cls.extract_due_date(text),
            "invoice_id": cls.extract_invoice_id(text),
            "transaction_id": cls.extract_transaction_id(text),
            "date_range": cls.extract_date_range(text),
        }

    @classmethod
    def extract_amount(cls, text: str) -> Optional[float]:
        """
        Extract numerical amount handling formats:
        - ₹5,000, Rs. 5000, INR 5000
        - $100, USD 100
        - 5k, 10k
        - 1.5 lakh / 2 lakhs
        - 15000.50
        """
        # 1. Lakhs check (e.g. 1.5 lakh, 2 lakhs)
        lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lac)s?", text, re.IGNORECASE)
        if lakh_match:
            try:
                return float(Decimal(lakh_match.group(1)) * 100000)
            except Exception:
                pass

        # 2. 'k' suffix check (e.g. ₹5k, 50k, 5 k)
        k_match = re.search(r"(?:₹|Rs\.?|INR|\$)?\s*(\d+(?:\.\d+)?)\s*k\b", text, re.IGNORECASE)
        if k_match:
            try:
                return float(Decimal(k_match.group(1)) * 1000)
            except Exception:
                pass

        # 3. Standard currency symbol or code with comma-separated numbers (e.g. ₹5,000.00, Rs 12,500, $450)
        curr_num_match = re.search(
            r"(?:₹|rs\.?|inr|\$|usd|eur|€|£)\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE,
        )
        if curr_num_match:
            num_str = curr_num_match.group(1).replace(",", "")
            try:
                val = float(num_str)
                if val > 0:
                    return val
            except Exception:
                pass

        # 4. Trailing currency notation (e.g. 5000 rs, 5000 inr, 100 dollars)
        post_curr_match = re.search(
            r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)\s*(?:rs|inr|rupees|usd|dollars|euro)",
            text,
            re.IGNORECASE,
        )
        if post_curr_match:
            num_str = post_curr_match.group(1).replace(",", "")
            try:
                val = float(num_str)
                if val > 0:
                    return val
            except Exception:
                pass

        # 5. Generic isolated number when user says "amount 5000" or "for 5000"
        for_num_match = re.search(r"(?:for|of|amount|value)\s*(?:₹|Rs\.?)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if for_num_match:
            num_str = for_num_match.group(1).replace(",", "")
            try:
                val = float(num_str)
                if val > 0:
                    return val
            except Exception:
                pass

        return None

    @classmethod
    def extract_currency(cls, text: str) -> str:
        """Detect currency from symbols or mentions."""
        text_lower = text.lower()
        if "$" in text or "usd" in text_lower or "dollar" in text_lower:
            return "USD"
        if "€" in text or "eur" in text_lower or "euro" in text_lower:
            return "EUR"
        if "£" in text or "gbp" in text_lower or "pound" in text_lower:
            return "GBP"
        return "INR"

    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        """Extract email address."""
        match = EMAIL_REGEX.search(text)
        return match.group(0) if match else None

    @classmethod
    def extract_invoice_id(cls, text: str) -> Optional[str]:
        """Extract invoice reference."""
        match = INVOICE_ID_REGEX.search(text)
        if match:
            inv = match.group(0).lstrip("#")
            return inv.upper() if inv.startswith("inv-") or inv.startswith("INV-") else inv
        return None

    @classmethod
    def extract_transaction_id(cls, text: str) -> Optional[str]:
        """Extract transaction reference."""
        match = TRANSACTION_ID_REGEX.search(text)
        return match.group(0) if match else None

    @classmethod
    def extract_customer_name(cls, text: str) -> Optional[str]:
        """
        Extract customer or client name.
        Looks for patterns like 'for Acme Corp', 'to Infosys', 'client Bharat Finserv', etc.
        """
        # Patterns with explicit keywords
        patterns = [
            r"(?:for client|client|to client|for customer|customer|to customer)\s+([A-Z][a-zA-Z0-9\s&.-]{2,30}?)(?:\s+(?:and|for|to|due|in|worth|with|amount|\.|\,|$))",
            r"(?:for|to)\s+([A-Z][a-zA-Z0-9&.-]+(?:\s+[A-Z][a-zA-Z0-9&.-]+){0,3})(?:\s+(?:and|for|to|due|in|worth|with|amount|\.|\,|$))",
        ]

        for p in patterns:
            match = re.search(p, text)
            if match:
                candidate = match.group(1).strip()
                # filter out non-names like 'January', 'Invoice', 'Monthly', 'USD'
                if candidate.lower() not in {"invoice", "monthly", "payment", "revenue", "reminder", "today", "tomorrow"}:
                    return candidate

        return None

    @classmethod
    def extract_due_date(cls, text: str) -> Optional[str]:
        """
        Extract due date or compute relative date.
        e.g., 'due in 15 days', 'due tomorrow', 'due 2026-12-15', 'due by next week'.
        """
        today = datetime.now()

        # ISO format YYYY-MM-DD
        iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if iso_match:
            return iso_match.group(1)

        # DD/MM/YYYY or DD-MM-YYYY
        dmy_match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
        if dmy_match:
            try:
                day, month, year = int(dmy_match.group(1)), int(dmy_match.group(2)), int(dmy_match.group(3))
                return f"{year:04d}-{month:02d}-{day:02d}"
            except Exception:
                pass

        text_lower = text.lower()
        if "tomorrow" in text_lower:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")

        if "next week" in text_lower:
            return (today + timedelta(days=7)).strftime("%Y-%m-%d")

        days_match = re.search(r"due (?:in|within)\s+(\d+)\s+days?", text_lower)
        if days_match:
            num_days = int(days_match.group(1))
            return (today + timedelta(days=num_days)).strftime("%Y-%m-%d")

        return None

    @classmethod
    def extract_description(cls, text: str) -> Optional[str]:
        """Extract description for the invoice or item."""
        patterns = [
            r"(?:for|description|service|work)\s+([a-zA-Z\s]{4,40}?)(?:\s+(?:amount|worth|due|to|for client|\.|\,|$))",
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                desc = match.group(1).strip()
                if desc.lower() not in {"client", "customer", "me", "an invoice", "invoice", "payment"}:
                    return desc
        return "Professional Services"

    @classmethod
    def extract_items(cls, text: str) -> Optional[List[Dict[str, Any]]]:
        """Generate structured items if amount is available."""
        amount = cls.extract_amount(text)
        desc = cls.extract_description(text) or "Consulting & Development"
        if amount:
            return [{"description": desc, "quantity": 1, "unit_price": amount}]
        return None

    @classmethod
    def extract_date_range(cls, text: str) -> Optional[str]:
        """Detect referenced time horizon."""
        text_lower = text.lower()
        if "this month" in text_lower:
            return "this_month"
        if "last month" in text_lower:
            return "last_month"
        if "this year" in text_lower:
            return "this_year"
        if "today" in text_lower:
            return "today"
        if "last 30 days" in text_lower or "past month" in text_lower:
            return "last_30_days"
        return None

    @classmethod
    def evaluate_missing_entities(cls, intent: str, entities: Dict[str, Any]) -> Tuple[List[str], bool]:
        """
        Checks if required fields are missing for an intent.
        Returns (missing_fields, clarification_needed).
        """
        missing = []
        if intent == "CREATE_INVOICE":
            if not entities.get("customer_name"):
                missing.append("customer_name")
            if not entities.get("amount"):
                missing.append("amount")

        elif intent == "PAYMENT_STATUS":
            if not entities.get("invoice_id") and not entities.get("transaction_id") and not entities.get("customer_name"):
                missing.append("invoice_id or customer_name")

        elif intent == "GENERATE_REMINDER":
            if not entities.get("invoice_id") and not entities.get("customer_name"):
                missing.append("invoice_id or customer_name")

        clarification_needed = len(missing) > 0
        return missing, clarification_needed

