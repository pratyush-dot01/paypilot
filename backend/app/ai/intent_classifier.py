"""
Intent Classifier Module for PayPilot AI (Phase 4).
Classifies natural language input into one of 9 recognized financial intents.
"""

import re
from typing import Tuple
import logging

logger = logging.getLogger("paypilot.ai.intent_classifier")

class IntentClassifier:
    """Classifies user queries into supported financial intents."""

    INTENT_KEYWORDS = {
        "CHECK_OVERDUE_INVOICES": [
            "overdue", "late payment", "past due", "delayed payment", "unpaid past due", "defaulted"
        ],
        "CHECK_PENDING_PAYMENTS": [
            "pending", "unpaid", "outstanding", "due invoices", "money owed", "awaiting payment",
            "receivables", "not yet paid", "who owes me", "balance due"
        ],
        "ANALYZE_REVENUE": [
            "revenue", "profit", "monthly revenue", "analyse", "analyze", "analytics",
            "compare", "financial performance", "sales", "earnings", "cash flow", "income",
            "growth", "margins", "run rate"
        ],
        "CREATE_INVOICE": [
            "create invoice", "generate invoice", "new invoice", "bill client", "raise an invoice",
            "make an invoice", "draft invoice", "bill for", "create bill", "invoice for"
        ],
        "GENERATE_REMINDER": [
            "reminder", "remind", "follow up", "chase invoice", "send notice", "payment reminder",
            "notify customer"
        ],
        "PAYMENT_STATUS": [
            "status of", "did they pay", "is paid", "payment status", "check status", "transaction status",
            "has client paid", "verify payment", "payment confirmation"
        ],
        "VIEW_TRANSACTIONS": [
            "transactions", "transaction history", "latest transactions", "payment history",
            "recent payments", "transaction logs", "show transactions", "list transactions"
        ],
        "VIEW_INVOICES": [
            "show invoices", "list invoices", "view invoices", "get invoices", "all invoices",
            "see invoices", "inspect invoices", "invoice list", "find invoice"
        ],
    }

    @classmethod
    def classify(cls, text: str) -> Tuple[str, float]:
        """
        Classify text into one of 9 intents with confidence score.
        Returns (intent, confidence).
        """
        text_lower = text.lower().strip()

        # Check for specific phrase matches in priority order
        # 1. Generate reminder (check first because user can say 'send reminder for overdue invoice')
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["GENERATE_REMINDER"]):
            return "GENERATE_REMINDER", 0.95

        # 2. Create invoice patterns
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["CREATE_INVOICE"]) or (
            ("invoice" in text_lower or "bill" in text_lower) and any(w in text_lower for w in ["create", "generate", "make", "raise", "send"])
        ):
            return "CREATE_INVOICE", 0.95

        # 3. Payment status of specific item
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["PAYMENT_STATUS"]) or (
            re.search(r"status.*(inv-|txn-)", text_lower)
        ):
            return "PAYMENT_STATUS", 0.90

        # 4. Check overdue invoices
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["CHECK_OVERDUE_INVOICES"]):
            return "CHECK_OVERDUE_INVOICES", 0.95

        # 5. Check pending / outstanding
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["CHECK_PENDING_PAYMENTS"]):
            return "CHECK_PENDING_PAYMENTS", 0.92

        # 6. View transactions
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["VIEW_TRANSACTIONS"]):
            return "VIEW_TRANSACTIONS", 0.91

        # 7. Analyze revenue / analytics
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["ANALYZE_REVENUE"]):
            return "ANALYZE_REVENUE", 0.92

        # 8. View invoices general
        if any(kw in text_lower for kw in cls.INTENT_KEYWORDS["VIEW_INVOICES"]) or (
            "invoices" in text_lower and any(w in text_lower for w in ["show", "list", "view", "find", "get"])
        ):
            return "VIEW_INVOICES", 0.88

        # 9. Default to General Financial Query
        return "GENERAL_FINANCIAL_QUERY", 0.70
