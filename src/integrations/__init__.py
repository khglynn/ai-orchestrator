"""External integrations for the AI Orchestrator"""

from .monday import MondayClient
from .slack import SlackClient

__all__ = ["MondayClient", "SlackClient"]
