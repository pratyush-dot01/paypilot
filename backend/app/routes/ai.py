"""
PayPilot AI API Endpoints (Phase 4).
Routes for AI chat, multi-turn conversation persistence, connectivity testing,
and dynamic suggestions.
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
import logging

from app.models.schemas import (
    AIChatRequest,
    AIChatResponse,
    ConversationSummary,
    ConversationDetail,
    AIStatusResponse,
    IntentType,
)
from app.ai.agent_controller import AgentController
from app.ai.conversation_manager import ConversationManager
from app.ai.llm_service import LLMService
from app.ai.prompts import SUGGESTED_PROMPT_TEMPLATES
from app.services.analytics_service import AnalyticsService

logger = logging.getLogger("paypilot.api.ai")

router = APIRouter(prefix="/api/ai", tags=["AI Intelligence Assistant (Phase 4)"])

@router.post("/chat", response_model=AIChatResponse)
async def chat_with_agent(payload: AIChatRequest):
    """
    Interact with PayPilot's autonomous financial agent.
    Selects tools, executes verified database & PayPal operations,
    enforces user confirmation for sensitive actions, and maintains multi-turn context.
    """
    try:
        response = await AgentController.process_chat(
            message=payload.message,
            conversation_id=payload.conversation_id,
            confirmed_action=payload.confirmed_action,
        )
        return response
    except Exception as e:
        logger.error(f"Error processing AI chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Agent error: {str(e)}",
        )

@router.get("/tools")
async def list_available_tools():
    """Retrieve catalog of all registered agent tools and input schemas."""
    from app.ai.tools.registry import ToolRegistry
    tools = ToolRegistry.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "requires_confirmation": t.requires_confirmation,
            "parameters": t.input_schema.model_json_schema(),
        }
        for t in tools
    ]

@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Retrieve list of conversation sessions."""
    try:
        conversations = await ConversationManager.list_conversations(limit=limit, skip=skip)
        return conversations
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations",
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str):
    """Retrieve complete message history for a conversation session."""
    conv = await ConversationManager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )
    return conv

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(conversation_id: str):
    """Delete a conversation session and all its messages."""
    deleted = await ConversationManager.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )
    return {"status": "success", "message": f"Conversation '{conversation_id}' deleted"}

@router.delete("/conversations/{conversation_id}/messages", status_code=status.HTTP_200_OK)
async def clear_conversation_messages(conversation_id: str):
    """Clear all turns from a conversation session."""
    cleared = await ConversationManager.clear_messages(conversation_id)
    if not cleared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )
    return {"status": "success", "message": f"Messages in '{conversation_id}' cleared"}

@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status():
    """Check AI LLM connectivity, active model, and supported intents."""
    connectivity = await LLMService.test_connectivity()
    return AIStatusResponse(
        status=connectivity.get("status", "unknown"),
        provider=connectivity.get("provider", "gemini"),
        model=connectivity.get("model", "gemini-1.5-flash"),
        api_key_configured=connectivity.get("api_key_configured", False),
        live_connectivity=connectivity.get("live_connectivity", False),
        latency_ms=connectivity.get("latency_ms"),
        supported_intents=[intent.value for intent in IntentType],
    )

@router.get("/suggested-prompts", response_model=List[str])
async def get_suggested_prompts():
    """
    Return dynamic context-aware suggestions based on current database status.
    e.g., if there are overdue invoices, prioritize overdue prompts.
    """
    try:
        stats = await AnalyticsService.get_dashboard_stats()
        prompts = []
        if stats.get("overdue_invoices", 0) > 0:
            prompts.append("Which invoices are overdue?")
            prompts.append("Generate a payment reminder for overdue clients")
        if stats.get("pending_payments", 0) > 0:
            prompts.append("Show my pending payments")
            prompts.append("Which unpaid invoice has the highest amount?")
        prompts.append("Analyse my monthly revenue")
        prompts.append("Create an invoice for ₹5,000 for TechCorp")
        prompts.append("Show my latest five transactions")

        return prompts[:6]
    except Exception:
        return SUGGESTED_PROMPT_TEMPLATES[:5]

