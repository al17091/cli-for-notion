"""Search command for notion-cli."""

import json
import sys
from typing import Optional

from notion_cli.client import NotionClient


def _get_title(item: dict) -> str:
    obj_type = item.get("object")
    if obj_type == "page":
        props = item.get("properties", {})
        for v in props.values():
            if isinstance(v, dict) and v.get("type") == "title":
                title_parts = v.get("title", [])
                return "".join([t.get("plain_text", "") for t in title_parts])
    elif obj_type == "database":
        title_parts = item.get("title", [])
        return "".join([t.get("plain_text", "") for t in title_parts])
    return "Untitled"


def cmd_search(
    client: NotionClient,
    query: str = "",
    filter_type: Optional[str] = None,
    limit: int = 20,
    as_json: bool = False,
) -> int:
    try:
        res = client.search(query=query, filter_type=filter_type, page_size=limit)

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        results = res.get("results", [])
        if not results:
            print(f"No results found for query: '{query}'")
            return 0

        print(f"Search results ({len(results)} found):\n")
        print(f"{'Type':<10} {'ID':<38} {'Title'}")
        print("-" * 80)
        for item in results:
            obj_type = item.get("object", "unknown")
            item_id = item.get("id", "")
            title = _get_title(item) or "Untitled"
            print(f"{obj_type:<10} {item_id:<38} {title}")
        return 0
    except Exception as e:
        sys.stderr.write(f"Search error: {e}\n")
        return 1
