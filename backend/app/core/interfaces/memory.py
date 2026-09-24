from typing import Protocol, List, Dict, Any

class MemoryProtocol(Protocol):
    def add_turn(self, conversation_id: str, query: str, answer: str) -> None:
        """Adds a conversation turn to the memory store."""
        ...
        
    def get_recent_turns(self, conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves the most recent conversation turns."""
        ...
        
    def get_history(self, conversation_id: str) -> str:
        """Formats the conversation history as a string for LLM context."""
        ...
        
    def clear_session(self, conversation_id: str) -> None:
        """Clears a specific conversation session."""
        ...
