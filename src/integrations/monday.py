"""Monday.com integration for creating and managing tasks/items"""

import os
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class MondayItem:
    """Represents an item/task on a Monday.com board"""
    id: str
    name: str
    board_id: str
    column_values: Dict[str, Any]


class MondayClient:
    """Client for interacting with Monday.com API"""

    API_URL = "https://api.monday.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Monday.com client.

        Args:
            api_key: Monday.com API key. If not provided, reads from MONDAY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("MONDAY_API_KEY")
        if not self.api_key:
            raise ValueError("Monday.com API key required. Set MONDAY_API_KEY env var or pass api_key.")

        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }

    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against Monday.com API"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.API_URL,
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                raise Exception(f"Monday.com API error: {result['errors']}")

            return result.get("data", {})

    async def get_boards(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Get list of boards accessible to the user"""
        query = """
        query ($limit: Int!) {
            boards(limit: $limit) {
                id
                name
                description
                state
            }
        }
        """
        result = await self._execute_query(query, {"limit": limit})
        return result.get("boards", [])

    async def get_board(self, board_id: str) -> Dict[str, Any]:
        """Get details of a specific board including columns"""
        query = """
        query ($boardId: [ID!]!) {
            boards(ids: $boardId) {
                id
                name
                description
                columns {
                    id
                    title
                    type
                }
                groups {
                    id
                    title
                }
            }
        }
        """
        result = await self._execute_query(query, {"boardId": [board_id]})
        boards = result.get("boards", [])
        return boards[0] if boards else {}

    async def get_items(self, board_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get items from a board"""
        query = """
        query ($boardId: [ID!]!, $limit: Int!) {
            boards(ids: $boardId) {
                items_page(limit: $limit) {
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                        }
                    }
                }
            }
        }
        """
        result = await self._execute_query(query, {"boardId": [board_id], "limit": limit})
        boards = result.get("boards", [])
        if boards:
            return boards[0].get("items_page", {}).get("items", [])
        return []

    async def create_item(
        self,
        board_id: str,
        item_name: str,
        group_id: Optional[str] = None,
        column_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new item/task on a Monday.com board.

        Args:
            board_id: The ID of the board (can extract from URL like monday.com/boards/18399052063)
            item_name: Name/title of the task
            group_id: Optional group ID to add the item to
            column_values: Optional dict of column values to set

        Returns:
            Created item data including ID
        """
        import json

        # Build the mutation
        if group_id and column_values:
            query = """
            mutation ($boardId: ID!, $itemName: String!, $groupId: String!, $columnValues: JSON!) {
                create_item(
                    board_id: $boardId,
                    item_name: $itemName,
                    group_id: $groupId,
                    column_values: $columnValues
                ) {
                    id
                    name
                }
            }
            """
            variables = {
                "boardId": board_id,
                "itemName": item_name,
                "groupId": group_id,
                "columnValues": json.dumps(column_values)
            }
        elif group_id:
            query = """
            mutation ($boardId: ID!, $itemName: String!, $groupId: String!) {
                create_item(
                    board_id: $boardId,
                    item_name: $itemName,
                    group_id: $groupId
                ) {
                    id
                    name
                }
            }
            """
            variables = {
                "boardId": board_id,
                "itemName": item_name,
                "groupId": group_id
            }
        elif column_values:
            query = """
            mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
                create_item(
                    board_id: $boardId,
                    item_name: $itemName,
                    column_values: $columnValues
                ) {
                    id
                    name
                }
            }
            """
            variables = {
                "boardId": board_id,
                "itemName": item_name,
                "columnValues": json.dumps(column_values)
            }
        else:
            query = """
            mutation ($boardId: ID!, $itemName: String!) {
                create_item(
                    board_id: $boardId,
                    item_name: $itemName
                ) {
                    id
                    name
                }
            }
            """
            variables = {
                "boardId": board_id,
                "itemName": item_name
            }

        result = await self._execute_query(query, variables)
        return result.get("create_item", {})

    async def update_item(
        self,
        board_id: str,
        item_id: str,
        column_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing item's column values.

        Args:
            board_id: The board ID
            item_id: The item ID to update
            column_values: Dict of column_id -> value to update
        """
        import json

        query = """
        mutation ($boardId: ID!, $itemId: ID!, $columnValues: JSON!) {
            change_multiple_column_values(
                board_id: $boardId,
                item_id: $itemId,
                column_values: $columnValues
            ) {
                id
                name
            }
        }
        """
        variables = {
            "boardId": board_id,
            "itemId": item_id,
            "columnValues": json.dumps(column_values)
        }

        result = await self._execute_query(query, variables)
        return result.get("change_multiple_column_values", {})

    async def add_update(self, item_id: str, body: str) -> Dict[str, Any]:
        """
        Add an update/comment to an item.

        Args:
            item_id: The item ID
            body: The update text content
        """
        query = """
        mutation ($itemId: ID!, $body: String!) {
            create_update(item_id: $itemId, body: $body) {
                id
                body
                created_at
            }
        }
        """
        result = await self._execute_query(query, {"itemId": item_id, "body": body})
        return result.get("create_update", {})

    @staticmethod
    def extract_board_id(url_or_id: str) -> str:
        """
        Extract board ID from a Monday.com URL or return as-is if already an ID.

        Examples:
            - "https://tecovas.monday.com/boards/18399052063" -> "18399052063"
            - "18399052063" -> "18399052063"
        """
        if url_or_id.startswith("http"):
            # Extract from URL
            parts = url_or_id.rstrip("/").split("/")
            for i, part in enumerate(parts):
                if part == "boards" and i + 1 < len(parts):
                    # Get the board ID, handling query params
                    board_id = parts[i + 1].split("?")[0]
                    return board_id
            raise ValueError(f"Could not extract board ID from URL: {url_or_id}")
        return url_or_id
