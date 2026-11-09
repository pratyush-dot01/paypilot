from fastapi import APIRouter
from app.models.schemas import ChatMessage, ChatResponse
from app.ai.agent_controller import AgentController
import logging

logger = logging.getLogger("paypilot.api.chat")

router = APIRouter(prefix="/api/chat", tags=["AI Assistant (Legacy Bridge)"])

@router.post("/", response_model=ChatResponse)
async def send_chat_message(payload: ChatMessage):
    """
    AI Assistant chat endpoint.
    Routes to the Phase 4 AgentController for grounded intelligence.
    """
    try:
        ai_resp = await AgentController.process_chat(
            message=payload.message,
            conversation_id=payload.session_id,
        )
        return ChatResponse(
            response=ai_resp.response,
            session_id=ai_resp.conversation_id,
        )
    except Exception as e:
        logger.warning(f"Error in AgentController bridge: {e}")
        return ChatResponse(
            response="Hello! I'm PayPilot AI. I can assist with generating invoices, viewing transactions, and analyzing your business cash flow.",
            session_id=payload.session_id or "default",
        )
