"""
Tool Registry Module for PayPilot AI Agent (Phase 5).
Central catalog of all available agent tools with safe execution,
Pydantic validation, and LLM schema generation.
"""

from typing import Dict, Any, List, Optional
import logging

from app.ai.tools.base import BaseTool
from app.ai.tools.invoice_tools import (
    CreateInvoiceTool,
    GetInvoiceTool,
    ListInvoicesTool,
    UpdateInvoiceTool,
    FindOverdueInvoicesTool,
)
from app.ai.tools.payment_tools import (
    CreatePayPalOrderTool,
    GetPaymentStatusTool,
    GetPaymentDetailsTool,
)
from app.ai.tools.customer_tools import (
    CreateCustomerTool,
    SearchCustomerTool,
    GetCustomerDetailsTool,
)
from app.ai.tools.reminder_tools import (
    GeneratePaymentReminderTool,
    CreateReminderTool,
)
from app.ai.tools.analytics_tools import (
    GetRevenueSummaryTool,
    GetPendingPaymentsTool,
    GetTransactionHistoryTool,
)
from app.ai.tools.automation_tools import (
    GetUpcomingInvoicesTool,
    GetFinancialAnalysisTool,
    DetectAnomaliesTool,
    PrepareOverdueRemindersTool,
    SendApprovedReminderTool,
    GetAutomationLogsTool,
)

logger = logging.getLogger("paypilot.ai.tools.registry")

class ToolRegistry:
    """Manages registration, discovery, and execution of agent tools."""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def initialize(cls):
        """Instantiate and register all available agent tools."""
        tool_instances = [
            # Invoices
            CreateInvoiceTool(),
            GetInvoiceTool(),
            ListInvoicesTool(),
            UpdateInvoiceTool(),
            FindOverdueInvoicesTool(),
            # Payments
            CreatePayPalOrderTool(),
            GetPaymentStatusTool(),
            GetPaymentDetailsTool(),
            # Customers
            CreateCustomerTool(),
            SearchCustomerTool(),
            GetCustomerDetailsTool(),
            # Reminders
            GeneratePaymentReminderTool(),
            CreateReminderTool(),
            # Analytics
            GetRevenueSummaryTool(),
            GetPendingPaymentsTool(),
            GetTransactionHistoryTool(),
            # Phase 6: Automation & Financial Intelligence
            GetUpcomingInvoicesTool(),
            GetFinancialAnalysisTool(),
            DetectAnomaliesTool(),
            PrepareOverdueRemindersTool(),
            SendApprovedReminderTool(),
            GetAutomationLogsTool(),
        ]
        cls._tools = {tool.name: tool for tool in tool_instances}
        logger.info(f"Initialized {len(cls._tools)} PayPilot agent tools in registry.")

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """Look up tool by name."""
        if not cls._tools:
            cls.initialize()
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[BaseTool]:
        """Return all registered tools."""
        if not cls._tools:
            cls.initialize()
        return list(cls._tools.values())

    @classmethod
    def get_function_definitions(cls) -> List[Dict[str, Any]]:
        """Return tool definitions in OpenAI/Gemini function declaration format."""
        if not cls._tools:
            cls.initialize()
        return [tool.to_function_def() for tool in cls._tools.values()]

    @classmethod
    async def execute_tool(cls, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Safely execute a tool with input validation and error containment."""
        tool = cls.get_tool(name)
        if not tool:
            return {
                "tool_name": name,
                "arguments": arguments,
                "success": False,
                "result": None,
                "error": f"Tool '{name}' is not registered or recognized",
            }
        return await tool.execute(arguments)

# Auto-initialize registry
ToolRegistry.initialize()

