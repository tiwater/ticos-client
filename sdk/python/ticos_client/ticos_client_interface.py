from abc import ABC, abstractmethod
from typing import Dict, Any


class MessageCallbackInterface(ABC):
    @abstractmethod
    def handle_message(self, message: Dict[str, Any]) -> bool:
        """Handle an incoming message. Should return True if handled successfully."""
        pass
