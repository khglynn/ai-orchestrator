"""Slack integration for reading conversations and posting messages"""

import os
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SlackMessage:
    """Represents a Slack message"""
    ts: str  # Timestamp (also serves as message ID)
    user: str
    text: str
    channel: str
    thread_ts: Optional[str] = None
    reactions: Optional[List[Dict]] = None


class SlackClient:
    """Client for interacting with Slack API"""

    API_URL = "https://slack.com/api"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize Slack client.

        Args:
            token: Slack Bot/User OAuth token. If not provided, reads from SLACK_TOKEN env var.
        """
        self.token = token or os.getenv("SLACK_TOKEN")
        if not self.token:
            raise ValueError("Slack token required. Set SLACK_TOKEN env var or pass token.")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def _api_call(self, method: str, **kwargs) -> Dict[str, Any]:
        """Make an API call to Slack"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_URL}/{method}",
                headers=self.headers,
                json=kwargs,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                raise Exception(f"Slack API error: {result.get('error', 'Unknown error')}")

            return result

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get information about a channel"""
        result = await self._api_call("conversations.info", channel=channel_id)
        return result.get("channel", {})

    async def get_channel_history(
        self,
        channel_id: str,
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None
    ) -> List[SlackMessage]:
        """
        Get message history from a channel.

        Args:
            channel_id: The channel ID
            limit: Max number of messages to return
            oldest: Only messages after this timestamp
            latest: Only messages before this timestamp
        """
        params = {"channel": channel_id, "limit": limit}
        if oldest:
            params["oldest"] = oldest
        if latest:
            params["latest"] = latest

        result = await self._api_call("conversations.history", **params)

        messages = []
        for msg in result.get("messages", []):
            messages.append(SlackMessage(
                ts=msg.get("ts", ""),
                user=msg.get("user", ""),
                text=msg.get("text", ""),
                channel=channel_id,
                thread_ts=msg.get("thread_ts"),
                reactions=msg.get("reactions")
            ))

        return messages

    async def get_thread_replies(
        self,
        channel_id: str,
        thread_ts: str,
        limit: int = 100
    ) -> List[SlackMessage]:
        """
        Get all replies in a thread.

        Args:
            channel_id: The channel ID
            thread_ts: The timestamp of the parent message
            limit: Max number of messages to return
        """
        result = await self._api_call(
            "conversations.replies",
            channel=channel_id,
            ts=thread_ts,
            limit=limit
        )

        messages = []
        for msg in result.get("messages", []):
            messages.append(SlackMessage(
                ts=msg.get("ts", ""),
                user=msg.get("user", ""),
                text=msg.get("text", ""),
                channel=channel_id,
                thread_ts=msg.get("thread_ts"),
                reactions=msg.get("reactions")
            ))

        return messages

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about a user"""
        result = await self._api_call("users.info", user=user_id)
        return result.get("user", {})

    async def post_message(
        self,
        channel_id: str,
        text: str,
        thread_ts: Optional[str] = None,
        blocks: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Post a message to a channel.

        Args:
            channel_id: The channel to post to
            text: The message text
            thread_ts: Optional thread timestamp to reply in thread
            blocks: Optional Block Kit blocks for rich formatting
        """
        params = {"channel": channel_id, "text": text}
        if thread_ts:
            params["thread_ts"] = thread_ts
        if blocks:
            params["blocks"] = blocks

        result = await self._api_call("chat.postMessage", **params)
        return result

    async def get_dm_history(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[SlackMessage]:
        """
        Get DM conversation history with a user.

        First opens/finds the DM channel, then gets history.
        """
        # Open DM channel with user
        result = await self._api_call("conversations.open", users=[user_id])
        channel_id = result.get("channel", {}).get("id")

        if not channel_id:
            raise Exception(f"Could not open DM with user {user_id}")

        return await self.get_channel_history(channel_id, limit=limit)

    @staticmethod
    def parse_message_url(url: str) -> Dict[str, str]:
        """
        Parse a Slack message URL to extract channel, message ts, and thread ts.

        Example URL:
        https://tecovas.slack.com/archives/C0257M3E57Y/p1770400863575629?thread_ts=1770394195.260059&cid=C0257M3E57Y

        Returns:
            Dict with 'channel_id', 'message_ts', and optionally 'thread_ts'
        """
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        result = {}

        # Extract channel ID from path (/archives/CHANNEL_ID/...)
        if "archives" in path_parts:
            archives_idx = path_parts.index("archives")
            if archives_idx + 1 < len(path_parts):
                result["channel_id"] = path_parts[archives_idx + 1]

        # Extract message timestamp from path (p1234567890123456 -> 1234567890.123456)
        if len(path_parts) > 0:
            for part in path_parts:
                if part.startswith("p") and part[1:].isdigit():
                    # Convert p1770400863575629 to 1770400863.575629
                    ts_str = part[1:]
                    result["message_ts"] = f"{ts_str[:-6]}.{ts_str[-6:]}"
                    break

        # Extract thread_ts from query params if present
        query_params = parse_qs(parsed.query)
        if "thread_ts" in query_params:
            result["thread_ts"] = query_params["thread_ts"][0]

        return result

    @staticmethod
    def format_conversation_for_summary(messages: List[SlackMessage], user_map: Dict[str, str] = None) -> str:
        """
        Format a list of messages into a readable conversation format.

        Args:
            messages: List of SlackMessage objects
            user_map: Optional dict mapping user IDs to display names
        """
        user_map = user_map or {}
        lines = []

        for msg in sorted(messages, key=lambda m: m.ts):
            user_display = user_map.get(msg.user, msg.user)
            lines.append(f"[{user_display}]: {msg.text}")

        return "\n".join(lines)
