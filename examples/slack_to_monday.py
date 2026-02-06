#!/usr/bin/env python3
"""
Example: Slack to Monday.com Workflow

This script demonstrates how to:
1. Read a Slack conversation/thread
2. Use AI to summarize key info and determine next steps
3. Create a task on Monday.com with the extracted information

Usage:
    export SLACK_TOKEN="xoxb-your-slack-token"
    export MONDAY_API_KEY="your-monday-api-key"
    export ANTHROPIC_API_KEY="your-anthropic-api-key"

    python examples/slack_to_monday.py --slack-url "https://slack.com/archives/..." --monday-board "18399052063"
"""

import asyncio
import argparse
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.integrations.slack import SlackClient
from src.integrations.monday import MondayClient

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


async def extract_task_info_with_ai(conversation_text: str) -> dict:
    """Use Claude to extract task info from a conversation."""
    if not HAS_ANTHROPIC:
        # Fallback if anthropic not installed
        return {
            "title": "Task from Slack conversation",
            "description": conversation_text[:500],
            "next_steps": ["Review the conversation", "Determine requirements", "Take action"]
        }

    client = anthropic.Anthropic()

    prompt = f"""Analyze this Slack conversation and extract:
1. A concise task title (max 10 words)
2. A brief description of what's being discussed/requested
3. 3-5 specific next steps or action items

Conversation:
{conversation_text}

Respond in this exact format:
TITLE: [task title]
DESCRIPTION: [brief description]
NEXT STEPS:
- [step 1]
- [step 2]
- [step 3]
"""

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse the response
    text = response.content[0].text
    result = {"title": "", "description": "", "next_steps": []}

    lines = text.strip().split("\n")
    current_section = None

    for line in lines:
        line = line.strip()
        if line.startswith("TITLE:"):
            result["title"] = line.replace("TITLE:", "").strip()
        elif line.startswith("DESCRIPTION:"):
            result["description"] = line.replace("DESCRIPTION:", "").strip()
        elif line.startswith("NEXT STEPS:"):
            current_section = "next_steps"
        elif current_section == "next_steps" and line.startswith("-"):
            result["next_steps"].append(line[1:].strip())

    return result


async def slack_to_monday_workflow(
    slack_url: str,
    monday_board_url_or_id: str,
    group_id: str = None
):
    """
    Complete workflow: Read Slack -> AI Summary -> Create Monday Task

    Args:
        slack_url: URL to the Slack message or thread
        monday_board_url_or_id: Monday.com board URL or ID
        group_id: Optional group ID on the Monday board
    """
    print("=" * 60)
    print("Slack to Monday.com Workflow")
    print("=" * 60)

    # Initialize clients
    slack = SlackClient()
    monday = MondayClient()

    # Parse the Slack URL
    parsed = SlackClient.parse_message_url(slack_url)
    channel_id = parsed.get("channel_id")
    thread_ts = parsed.get("thread_ts") or parsed.get("message_ts")

    if not channel_id:
        raise ValueError(f"Could not parse channel ID from URL: {slack_url}")

    print(f"\n1. Reading Slack conversation from channel {channel_id}...")

    # Get thread messages
    if thread_ts:
        messages = await slack.get_thread_replies(channel_id, thread_ts)
    else:
        messages = await slack.get_channel_history(channel_id, limit=20)

    # Get user info for better display
    user_ids = set(msg.user for msg in messages if msg.user)
    user_map = {}
    for uid in user_ids:
        try:
            user_info = await slack.get_user_info(uid)
            user_map[uid] = user_info.get("real_name", user_info.get("name", uid))
        except Exception:
            user_map[uid] = uid

    # Format conversation
    conversation_text = SlackClient.format_conversation_for_summary(messages, user_map)
    print(f"   Found {len(messages)} messages")
    print("\n   Conversation preview:")
    print("   " + "-" * 40)
    for line in conversation_text.split("\n")[:5]:
        print(f"   {line[:70]}...")
    print("   " + "-" * 40)

    # Use AI to extract task info
    print("\n2. Analyzing conversation with AI...")
    task_info = await extract_task_info_with_ai(conversation_text)
    print(f"   Title: {task_info['title']}")
    print(f"   Description: {task_info['description'][:100]}...")
    print(f"   Next steps: {len(task_info['next_steps'])} items")

    # Create Monday.com task
    print("\n3. Creating task on Monday.com...")
    board_id = MondayClient.extract_board_id(monday_board_url_or_id)

    # Get board info to understand columns
    board_info = await monday.get_board(board_id)
    print(f"   Board: {board_info.get('name', 'Unknown')}")

    # Build the item description
    description_parts = [
        task_info["description"],
        "",
        "**Next Steps:**",
    ] + [f"- {step}" for step in task_info["next_steps"]] + [
        "",
        f"**Source:** {slack_url}"
    ]
    full_description = "\n".join(description_parts)

    # Create the item
    created_item = await monday.create_item(
        board_id=board_id,
        item_name=task_info["title"],
        group_id=group_id
    )

    print(f"   Created item: {created_item.get('name')} (ID: {created_item.get('id')})")

    # Add the description as an update/comment
    if created_item.get("id"):
        await monday.add_update(created_item["id"], full_description)
        print("   Added description as update")

    print("\n" + "=" * 60)
    print("Workflow complete!")
    print(f"Task created: {task_info['title']}")
    print("=" * 60)

    return created_item


def main():
    parser = argparse.ArgumentParser(
        description="Create a Monday.com task from a Slack conversation"
    )
    parser.add_argument(
        "--slack-url",
        required=True,
        help="URL to the Slack message or thread"
    )
    parser.add_argument(
        "--monday-board",
        required=True,
        help="Monday.com board URL or ID"
    )
    parser.add_argument(
        "--group-id",
        help="Optional Monday.com group ID"
    )

    args = parser.parse_args()

    # Run the async workflow
    result = asyncio.run(slack_to_monday_workflow(
        slack_url=args.slack_url,
        monday_board_url_or_id=args.monday_board,
        group_id=args.group_id
    ))

    return result


if __name__ == "__main__":
    main()
