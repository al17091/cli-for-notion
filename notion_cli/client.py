"""
Notion API Client for notion-cli.
Zero-dependency, uses standard library urllib.request.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2026-03-11"
CONFIG_FILE_PATH = os.path.expanduser("~/.config/notion/config.json")


def normalize_id(identifier: str) -> str:
    """Normalize a Notion ID, URL, or hex string to standard 8-4-4-4-12 UUID format.

    Examples:
        - 3e76bf4b-dc72-813f-a377-c987fc046733 -> 3e76bf4b-dc72-813f-a377-c987fc046733
        - 3e76bf4bdc72813fa377c987fc046733 -> 3e76bf4b-dc72-813f-a377-c987fc046733
        - https://notion.so/Page-Title-3e76bf4bdc72813fa377c987fc046733 -> 3e76bf4b-dc72-813f-a377-c987fc046733
        - https://app.notion.com/p/3e76bf4bdc72813fa377c987fc046733 -> 3e76bf4b-dc72-813f-a377-c987fc046733
    """
    clean = identifier.strip().split("?")[0].rstrip("/")
    # Check for 32 hex chars with or without hyphens
    match = re.search(r"([0-9a-fA-F]{8})-?([0-9a-fA-F]{4})-?([0-9a-fA-F]{4})-?([0-9a-fA-F]{4})-?([0-9a-fA-F]{12})", clean)
    if match:
        return f"{match.group(1).lower()}-{match.group(2).lower()}-{match.group(3).lower()}-{match.group(4).lower()}-{match.group(5).lower()}"

    # Also match raw 32 hex chars anywhere
    match32 = re.search(r"([0-9a-fA-F]{32})", clean)
    if match32:
        h = match32.group(1).lower()
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

    return identifier.strip()


def load_token(explicit_token: Optional[str] = None) -> str:
    """Load token from flag, env var, or config file."""
    if explicit_token:
        return explicit_token.strip()

    env_token = os.environ.get("NOTION_API_KEY") or os.environ.get("NOTION_TOKEN")
    if env_token:
        return env_token.strip()

    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("token") or data.get("notion_api_key")
                if token:
                    return token.strip()
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to read {CONFIG_FILE_PATH}: {e}\n")

    raise ValueError(
        "No Notion token found. Provide --token, set NOTION_API_KEY env var, "
        "or run 'notion auth set-token <token>' to save to ~/.config/notion/config.json."
    )


def save_token(token: str) -> None:
    """Save token to ~/.config/notion/config.json with 0600 permissions."""
    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump({"token": token.strip()}, f, indent=2)
    os.chmod(CONFIG_FILE_PATH, 0o600)


class NotionAPIError(Exception):
    def __init__(self, status: int, code: str, message: str, raw_response: Dict[str, Any]):
        self.status = status
        self.code = code
        self.message = message
        self.raw_response = raw_response
        super().__init__(f"[{status} {code}] {message}")


class NotionClient:
    def __init__(self, token: Optional[str] = None, debug: bool = False):
        self.token = load_token(token)
        self.debug = debug

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "notion-cli/1.0",
        }

    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Execute Notion API HTTP request with retry on 429 rate limits."""
        url = f"{NOTION_API_BASE.rstrip('/')}/{endpoint.lstrip('/')}"
        if params:
            query = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url = f"{url}?{query}"

        data = json.dumps(json_data).encode("utf-8") if json_data is not None else None

        if self.debug:
            sys.stderr.write(f"[DEBUG] {method} {url}\n")
            if json_data:
                sys.stderr.write(f"[DEBUG] Body: {json.dumps(json_data, indent=2)}\n")

        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_body = resp.read().decode("utf-8")
                    if resp_body:
                        return json.loads(resp_body)
                    return {}
            except urllib.error.HTTPError as e:
                err_body_raw = e.read().decode("utf-8")
                err_json = {}
                try:
                    err_json = json.loads(err_body_raw)
                except Exception:
                    pass

                # Rate limiting (429) retry
                if e.code == 429 and attempt < retries - 1:
                    retry_after = int(e.headers.get("Retry-After", 1))
                    if self.debug:
                        sys.stderr.write(f"[DEBUG] 429 Rate limit, waiting {retry_after}s...\n")
                    time.sleep(retry_after)
                    continue

                code = err_json.get("code", "unknown_error")
                message = err_json.get("message", err_body_raw or str(e))
                raise NotionAPIError(e.code, code, message, err_json) from None

        raise NotionAPIError(500, "retry_exhausted", "Exhausted retries on request", {})

    # -------------------------------------------------------------
    # User / Auth
    # -------------------------------------------------------------
    def get_me(self) -> Dict[str, Any]:
        return self.request("GET", "users/me")

    # -------------------------------------------------------------
    # Pages
    # -------------------------------------------------------------
    def get_page(self, page_id: str) -> Dict[str, Any]:
        normalized = normalize_id(page_id)
        return self.request("GET", f"pages/{normalized}")

    def get_page_markdown(self, page_id: str, include_transcript: bool = False) -> str:
        normalized = normalize_id(page_id)
        params = {"include_transcript": "true"} if include_transcript else None
        res = self.request("GET", f"pages/{normalized}/markdown", params=params)
        return res.get("markdown", "")

    def create_page(
        self,
        parent_id: str,
        title: str,
        is_parent_db: bool = False,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_parent = normalize_id(parent_id)

        props: Dict[str, Any] = {}
        title_key = "title"

        if is_parent_db:
            parent_payload = {"type": "database_id", "database_id": normalized_parent}
            # Attempt to discover the exact title property name and schemas
            try:
                db_info = self.get_database(normalized_parent)
                db_props = db_info.get("properties", {})
                for p_name, p_val in db_props.items():
                    if p_val.get("type") == "title":
                        title_key = p_name
                        break
            except Exception:
                title_key = "Title"
        else:
            parent_payload = {"type": "page_id", "page_id": normalized_parent}

        if properties:
            props.update(properties)

        # Ensure title is set if not provided
        if title_key not in props and "title" not in props and "Name" not in props:
            props[title_key] = [{"type": "text", "text": {"content": title}}]
        elif title_key in props and isinstance(props[title_key], str):
            props[title_key] = [{"type": "text", "text": {"content": props[title_key]}}]

        payload: Dict[str, Any] = {
            "parent": parent_payload,
            "properties": props,
        }
        return self.request("POST", "pages", json_data=payload)

    def set_page_title(self, page_id: str, new_title: str) -> Dict[str, Any]:
        normalized = normalize_id(page_id)
        # Fetch current page to detect the exact title property name
        page = self.get_page(normalized)
        title_prop_name = "title"
        for prop_name, prop_data in page.get("properties", {}).items():
            if prop_data.get("type") == "title":
                title_prop_name = prop_name
                break

        payload = {
            "properties": {
                title_prop_name: [{"type": "text", "text": {"content": new_title}}]
            }
        }
        return self.request("PATCH", f"pages/{normalized}", json_data=payload)

    def update_page_markdown(
        self, page_id: str, markdown: str, allow_delete: bool = False
    ) -> Dict[str, Any]:
        """Replace the entire markdown content of the page."""
        normalized = normalize_id(page_id)
        payload = {
            "type": "replace_content",
            "replace_content": {
                "new_str": markdown,
                "allow_deleting_content": allow_delete,
            },
        }
        return self.request("PATCH", f"pages/{normalized}/markdown", json_data=payload)

    def append_page_markdown(self, page_id: str, markdown: str) -> Dict[str, Any]:
        """Append markdown content at the end of the page."""
        normalized = normalize_id(page_id)
        payload = {
            "type": "insert_content",
            "insert_content": {
                "content": markdown,
                "position": {"type": "end"},
            },
        }
        return self.request("PATCH", f"pages/{normalized}/markdown", json_data=payload)

    def replace_page_markdown_text(
        self, page_id: str, old_str: str, new_str: str, replace_all: bool = False
    ) -> Dict[str, Any]:
        """Targeted find-and-replace of markdown string within the page."""
        normalized = normalize_id(page_id)
        payload = {
            "type": "update_content",
            "update_content": {
                "content_updates": [
                    {
                        "old_str": old_str,
                        "new_str": new_str,
                        "replace_all_matches": replace_all,
                    }
                ],
                "allow_deleting_content": False,
            },
        }
        return self.request("PATCH", f"pages/{normalized}/markdown", json_data=payload)

    def delete_page(self, page_id: str) -> Dict[str, Any]:
        """Move page to trash."""
        normalized = normalize_id(page_id)
        payload = {"in_trash": True}
        return self.request("PATCH", f"pages/{normalized}", json_data=payload)

    # -------------------------------------------------------------
    # Databases & Data Sources
    # -------------------------------------------------------------
    def get_database(self, database_id: str) -> Dict[str, Any]:
        """Retrieve database metadata and its schema (via data_source if applicable)."""
        normalized = normalize_id(database_id)
        # Try fetching as database
        try:
            db_res = self.request("GET", f"databases/{normalized}")
            data_sources = db_res.get("data_sources", [])
            if data_sources and isinstance(data_sources, list):
                # Retrieve properties from primary data source
                ds_id = data_sources[0].get("id")
                if ds_id:
                    try:
                        ds_res = self.request("GET", f"data_sources/{ds_id}")
                        if "properties" in ds_res:
                            db_res["properties"] = ds_res["properties"]
                            db_res["data_source_id"] = ds_id
                    except Exception:
                        pass
            return db_res
        except NotionAPIError as e:
            if e.status in (400, 404):
                # Maybe it is directly a data_source_id
                return self.request("GET", f"data_sources/{normalized}")
            raise

    def resolve_data_source_id(self, identifier: str) -> str:
        """Resolve a database_id or data_source_id into a queryable data_source_id."""
        normalized = normalize_id(identifier)
        # Try as data_source directly
        try:
            self.request("GET", f"data_sources/{normalized}")
            return normalized
        except NotionAPIError:
            pass

        # Try as database and find data_sources[0]
        try:
            db_res = self.request("GET", f"databases/{normalized}")
            data_sources = db_res.get("data_sources", [])
            if data_sources and len(data_sources) > 0:
                return data_sources[0].get("id", normalized)
        except Exception:
            pass

        return normalized

    def query_database(
        self,
        database_id: str,
        filter_dict: Optional[Dict[str, Any]] = None,
        sorts_list: Optional[List[Dict[str, Any]]] = None,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        ds_id = self.resolve_data_source_id(database_id)
        payload: Dict[str, Any] = {"page_size": min(page_size, 100)}
        if filter_dict:
            payload["filter"] = filter_dict
        if sorts_list:
            payload["sorts"] = sorts_list
        return self.request("POST", f"data_sources/{ds_id}/query", json_data=payload)

    # -------------------------------------------------------------
    # Search
    # -------------------------------------------------------------
    def search(
        self,
        query: str = "",
        filter_type: Optional[str] = None,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"page_size": min(page_size, 100)}
        if query:
            payload["query"] = query
        if filter_type in ("page", "database"):
            payload["filter"] = {"property": "object", "value": filter_type}
        return self.request("POST", "search", json_data=payload)
