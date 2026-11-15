"""Auth commands for notion-cli."""

import json
import sys
from typing import Any, Dict

from notion_cli.client import NotionClient, save_token


def cmd_auth_status(client: NotionClient, as_json: bool = False) -> int:
    try:
        user = client.get_me()
        if as_json:
            print(json.dumps(user, indent=2, ensure_ascii=False))
            return 0

        bot_info = user.get("bot", {})
        workspace_name = bot_info.get("workspace_name", "Unknown Workspace")
        bot_name = user.get("name", "Unknown Bot")
        bot_id = user.get("id", "")

        print(f"Authenticated as: {bot_name} ({bot_id})")
        print(f"Workspace:        {workspace_name}")
        print("Status:           Active (Valid token)")
        return 0
    except Exception as e:
        sys.stderr.write(f"Authentication failed: {e}\n")
        return 1


def cmd_auth_set_token(token: str) -> int:
    try:
        save_token(token)
        # Test the newly saved token
        client = NotionClient(token=token)
        user = client.get_me()
        workspace = user.get("bot", {}).get("workspace_name", "Unknown")
        print(f"Token saved successfully to ~/.config/notion/config.json")
        print(f"Verified connection to workspace: {workspace} (Bot: {user.get('name')})")
        return 0
    except Exception as e:
        sys.stderr.write(f"Failed to verify or save token: {e}\n")
        return 1
