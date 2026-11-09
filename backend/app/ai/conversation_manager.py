"""
Conversation Manager Module for PayPilot AI (Phase 4).
Manages multi-turn conversation sessions, history retrieval,
context retention, and persistence in MongoDB.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from app.database import db_manager

logger = logging.getLogger("paypilot.ai.conversation_manager")

class ConversationManager:
    """Manages conversational state, session continuity, and multi-turn context."""

    @classmethod
    def generate_conversation_id(cls) -> str:
        """Create a new unique conversation ID."""
        return f"conv_{uuid.uuid4().hex[:12]}"

    @classmethod
    async def get_or_create_conversation(cls, conversation_id: Optional[str] = None) -> str:
        """Ensure valid conversation exists, return conversation_id."""
        if not conversation_id or conversation_id.strip() == "":
            conversation_id = cls.generate_conversation_id()

        existing = await db_manager.ai_conversations.find_one({"conversation_id": conversation_id})
        if not existing:
            now_iso = datetime.utcnow().isoformat()
            new_conv = {
                "conversation_id": conversation_id,
                "created_at": now_iso,
                "updated_at": now_iso,
                "turn_count": 0,
                "last_intent": None,
                "turns": [],
            }
            await db_manager.ai_conversations.insert_one(new_conv)

        return conversation_id

    @classmethod
    async def add_turn(
        cls,
        conversation_id: str,
        role: str,
        message: str,
        intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a single message turn in the conversation."""
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.utcnow().isoformat()

        turn = {
            "turn_id": turn_id,
            "role": role,
            "message": message,
            "intent": intent,
            "entities": entities or {},
            "timestamp": now_iso,
        }

        conv = await db_manager.ai_conversations.find_one({"conversation_id": conversation_id})
        if not conv:
            await cls.get_or_create_conversation(conversation_id)
            conv = await db_manager.ai_conversations.find_one({"conversation_id": conversation_id})

        turns = conv.get("turns", []) if conv else []
        turns.append(turn)

        update_doc = {
            "$set": {
                "turns": turns,
                "turn_count": len(turns),
                "updated_at": now_iso,
                "last_message": message[:120],
                "last_intent": intent or conv.get("last_intent"),
            }
        }

        await db_manager.ai_conversations.update_one({"conversation_id": conversation_id}, update_doc)
        return turn

    @classmethod
    async def get_history(cls, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent conversation turns for context."""
        conv = await db_manager.ai_conversations.find_one({"conversation_id": conversation_id})
        if not conv:
            return []
        turns = conv.get("turns", [])
        return turns[-limit:] if limit else turns

    @classmethod
    async def get_conversation(cls, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full conversation details."""
        conv = await db_manager.ai_conversations.find_one({"conversation_id": conversation_id})
        if not conv:
            return None
        return {
            "conversation_id": conv.get("conversation_id"),
            "created_at": conv.get("created_at"),
            "updated_at": conv.get("updated_at"),
            "turns": conv.get("turns", []),
        }

    @classmethod
    async def list_conversations(cls, limit: int = 20, skip: int = 0) -> List[Dict[str, Any]]:
        """List recent conversations with summary statistics."""
        cursor = db_manager.ai_conversations.find({}).sort("updated_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(limit)

        results = []
        for c in items:
            turns = c.get("turns", [])
            last_msg = c.get("last_message", "")
            if not last_msg and turns:
                last_msg = turns[-1].get("message", "")[:120]

            results.append({
                "conversation_id": c.get("conversation_id"),
                "turn_count": len(turns),
                "last_message": last_msg,
                "last_intent": c.get("last_intent"),
                "created_at": c.get("created_at"),
                "updated_at": c.get("updated_at"),
            })
        return results

    @classmethod
    async def delete_conversation(cls, conversation_id: str) -> bool:
        """Permanently delete a conversation session."""
        res = await db_manager.ai_conversations.delete_one({"conversation_id": conversation_id})
        return getattr(res, "deleted_count", 0) > 0

    @classmethod
    async def clear_messages(cls, conversation_id: str) -> bool:
        """Clear message turns while preserving the conversation container."""
        now_iso = datetime.utcnow().isoformat()
        res = await db_manager.ai_conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": {"turns": [], "turn_count": 0, "updated_at": now_iso, "last_message": ""}}
        )
        return getattr(res, "modified_count", 0) > 0

    @classmethod
    async def set_pending_action(cls, conversation_id: str, action: Dict[str, Any]) -> None:
        """Store pending action awaiting explicit user confirmation."""
        await db_manager.ai_conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": {"pending_action": action, "updated_at": datetime.utcnow().isoformat()}}
        )

    @classmethod
    async def get_pending_action(cls, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve any pending action requiring confirmation."""
        conv = await db_manager.ai_conversations.find_one({"conversation_id": conversation_id})
        return conv.get("pending_action") if conv else None

    @classmethod
    async def clear_pending_action(cls, conversation_id: str) -> None:
        """Clear pending action once executed or rejected."""
        await db_manager.ai_conversations.update_one(
            {"conversation_id": conversation_id},
            {"$set": {"pending_action": None, "updated_at": datetime.utcnow().isoformat()}}
        )

