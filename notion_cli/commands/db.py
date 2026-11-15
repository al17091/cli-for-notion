"""Database commands for notion-cli."""

import json
import sys
from typing import Any, Dict, List, Optional

from notion_cli.client import NotionClient, normalize_id


def _extract_title(props: Dict[str, Any]) -> str:
    for v in props.values():
        if isinstance(v, dict) and v.get("type") == "title":
            title_parts = v.get("title", [])
            return "".join([t.get("plain_text", "") for t in title_parts])
    return "Untitled"


def cmd_db_get(
    client: NotionClient,
    database_id: str,
    as_json: bool = False,
) -> int:
    try:
        normalized = normalize_id(database_id)
        db_obj = client.get_database(normalized)

        if as_json:
            print(json.dumps(db_obj, indent=2, ensure_ascii=False))
            return 0

        title_parts = db_obj.get("title", [])
        title = "".join([t.get("plain_text", "") for t in title_parts]) or "Untitled Database"
        print(f"Database: {title}")
        print(f"ID:       {db_obj.get('id')}")
        print(f"URL:      {db_obj.get('url')}")
        print("\nProperties:")
        for name, p_data in db_obj.get("properties", {}).items():
            p_type = p_data.get("type", "unknown")
            print(f"  - {name}: ({p_type})")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error retrieving database {database_id}: {e}\n")
        return 1


def cmd_db_query(
    client: NotionClient,
    database_id: str,
    filter_json: Optional[str] = None,
    sorts_json: Optional[str] = None,
    limit: int = 50,
    as_json: bool = False,
) -> int:
    try:
        normalized = normalize_id(database_id)
        filter_dict = json.loads(filter_json) if filter_json else None
        sorts_list = json.loads(sorts_json) if sorts_json else None

        res = client.query_database(
            database_id=normalized,
            filter_dict=filter_dict,
            sorts_list=sorts_list,
            page_size=limit,
        )

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        results = res.get("results", [])
        print(f"Found {len(results)} items in database {normalized}:\n")
        print(f"{'ID':<38}  {'Title'}")
        print("-" * 80)
        for row in results:
            item_id = row.get("id", "")
            title = _extract_title(row.get("properties", {}))
            print(f"{item_id:<38}  {title}")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error querying database {database_id}: {e}\n")
        return 1


def _format_db_properties(schema: Dict[str, Any], raw_props: Dict[str, Any]) -> Dict[str, Any]:
    """Format user-provided properties dictionary into Notion API 2026-03-11 format."""
    formatted: Dict[str, Any] = {}
    for key, val in raw_props.items():
        if key in schema:
            prop_type = schema[key].get("type")
            if prop_type == "select":
                if isinstance(val, str):
                    formatted[key] = {"name": val}
                elif isinstance(val, dict) and "select" in val:
                    formatted[key] = val["select"]
                else:
                    formatted[key] = val
            elif prop_type == "status":
                if isinstance(val, str):
                    formatted[key] = {"name": val}
                elif isinstance(val, dict) and "status" in val:
                    formatted[key] = val["status"]
                else:
                    formatted[key] = val
            elif prop_type == "multi_select":
                if isinstance(val, list):
                    formatted[key] = [{"name": x} if isinstance(x, str) else x for x in val]
                elif isinstance(val, str):
                    formatted[key] = [{"name": val}]
                else:
                    formatted[key] = val
            elif prop_type == "rich_text":
                if isinstance(val, str):
                    formatted[key] = [{"text": {"content": val}}]
                elif isinstance(val, dict) and "rich_text" in val:
                    formatted[key] = val["rich_text"]
                else:
                    formatted[key] = val
            else:
                formatted[key] = val
        else:
            # Fallback if property not explicitly found in schema
            if isinstance(val, dict) and "select" in val:
                formatted[key] = val["select"]
            elif isinstance(val, dict) and "rich_text" in val:
                formatted[key] = val["rich_text"]
            else:
                formatted[key] = val
    return formatted


def cmd_db_add_item(
    client: NotionClient,
    database_id: str,
    title: str,
    props_json: Optional[str] = None,
    as_json: bool = False,
) -> int:
    try:
        normalized = normalize_id(database_id)
        raw_props = json.loads(props_json) if props_json else {}

        # Fetch schema to format properties cleanly
        db_info = client.get_database(normalized)
        schema = db_info.get("properties", {})
        properties = _format_db_properties(schema, raw_props)

        res = client.create_page(
            parent_id=normalized,
            title=title,
            is_parent_db=True,
            properties=properties,
        )

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        new_id = res.get("id")
        url = res.get("url", "")
        print(f"Database item created successfully!")
        print(f"Title: {title}")
        print(f"ID:    {new_id}")
        print(f"URL:   {url}")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error adding item to database {database_id}: {e}\n")
        return 1
