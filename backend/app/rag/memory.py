import datetime
from typing import Dict, List, Any, Optional

from app.core.interfaces.memory import MemoryProtocol
from app.schemas.chat import ChatProfile, ConversationState

class InMemorySessionStore(MemoryProtocol):
    """
    In-memory store for SIH demo. 
    WARNING: This resets when the server restarts.
    """
    def __init__(self):
        self._SESSIONS: Dict[str, Dict[str, Any]] = {}

    def _ensure_session(self, conversation_id: str):
        if conversation_id not in self._SESSIONS:
            self._SESSIONS[conversation_id] = {
                "turns": [],
                "profile": ChatProfile().model_dump()
            }

    def add_turn(self, conversation_id: str, query: str, answer: str) -> None:
        """Adds a conversation turn to the memory store."""
        if not conversation_id:
            return
            
        self._ensure_session(conversation_id)
            
        self._SESSIONS[conversation_id]["turns"].append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        
        # Keep only the last 5 turns maximum
        if len(self._SESSIONS[conversation_id]["turns"]) > 5:
            self._SESSIONS[conversation_id]["turns"] = self._SESSIONS[conversation_id]["turns"][-5:]

    def get_recent_turns(self, conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves the most recent conversation turns."""
        if not conversation_id or conversation_id not in self._SESSIONS:
            return []
        return self._SESSIONS[conversation_id]["turns"][-limit:]

    def get_history(self, conversation_id: str) -> str:
        """Formats the conversation history as a string for LLM context."""
        turns = self.get_recent_turns(conversation_id)
        if not turns:
            return ""
            
        history = []
        for turn in turns:
            history.append(f"- User: {turn['query']}")
            history.append(f"- Assistant: {turn['answer']}")
        return "\n".join(history)

    def get_session_profile(self, conversation_id: str) -> ChatProfile:
        if not conversation_id:
            return ChatProfile()
        self._ensure_session(conversation_id)
        return ChatProfile(**self._SESSIONS[conversation_id]["profile"])

    def update_session_profile(self, conversation_id: str, profile: ChatProfile) -> None:
        if not conversation_id:
            return
        self._ensure_session(conversation_id)
        # Merge existing profile with new non-null values
        existing = self._SESSIONS[conversation_id]["profile"]
        new_data = profile.model_dump(exclude_unset=True, exclude_none=True)
        existing.update(new_data)
        self._SESSIONS[conversation_id]["profile"] = existing

    def clear_session(self, conversation_id: str) -> None:
        """Clears a specific conversation session."""
        if conversation_id in self._SESSIONS:
            del self._SESSIONS[conversation_id]

# Global instance for use by endpoints
store = InMemorySessionStore()

# Helper aliases to preserve existing codebase references without breaking
def add_turn(*args, **kwargs): return store.add_turn(*args, **kwargs)
def get_recent_turns(*args, **kwargs): return store.get_recent_turns(*args, **kwargs)
def get_history(*args, **kwargs): return store.get_history(*args, **kwargs)
def clear_session(*args, **kwargs): return store.clear_session(*args, **kwargs)
def get_session_profile(*args, **kwargs): return store.get_session_profile(*args, **kwargs)
def update_session_profile(*args, **kwargs): return store.update_session_profile(*args, **kwargs)

