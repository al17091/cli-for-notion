"""Page commands for notion-cli."""

import json
import os
import sys
from typing import Optional

from cli_for_notion.client import NotionClient, normalize_id


def _read_content_input(file_path: Optional[str], content_str: Optional[str]) -> Optional[str]:
    """Read content from string, file path, or stdin."""
    if content_str is not None:
        # Convert literal escaped \n and \t if present in CLI argument
        return content_str.replace("\\n", "\n").replace("\\t", "\t")

    if file_path == "-" or (file_path is None and not sys.stdin.isatty()):
        return sys.stdin.read()

    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    return None


def _get_page_title(page_obj: dict) -> str:
    """Helper to extract title text from page object."""
    props = page_obj.get("properties", {})
    for val in props.values():
        if isinstance(val, dict) and val.get("type") == "title":
            title_parts = val.get("title", [])
            return "".join([t.get("plain_text", "") for t in title_parts])
    return "Untitled"


def cmd_page_get(
    client: NotionClient,
    page_id: str,
    output_path: Optional[str] = None,
    as_json: bool = False,
    include_transcript: bool = False,
) -> int:
    try:
        normalized = normalize_id(page_id)
        if as_json:
            data = client.get_page(normalized)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return 0

        md = client.get_page_markdown(normalized, include_transcript=include_transcript)
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Saved page markdown to {output_path}")
        else:
            sys.stdout.write(md)
            if not md.endswith("\n"):
                sys.stdout.write("\n")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error fetching page {page_id}: {e}\n")
        return 1


def cmd_page_create(
    client: NotionClient,
    parent_id: str,
    title: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    is_parent_db: bool = False,
    as_json: bool = False,
) -> int:
    try:
        # Step 1: Create the page
        created = client.create_page(
            parent_id=parent_id,
            title=title,
            is_parent_db=is_parent_db,
        )
        new_id = created.get("id")
        page_url = created.get("url", "")

        # Step 2: If markdown content was specified, populate it
        initial_body = _read_content_input(file_path, content)
        if initial_body:
            client.update_page_markdown(new_id, initial_body, allow_delete=True)

        if as_json:
            print(json.dumps(created, indent=2, ensure_ascii=False))
            return 0

        print(f"Page created successfully!")
        print(f"Title: {title}")
        print(f"ID:    {new_id}")
        print(f"URL:   {page_url}")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error creating page: {e}\n")
        return 1


def cmd_page_update(
    client: NotionClient,
    page_id: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    allow_delete: bool = False,
    as_json: bool = False,
) -> int:
    try:
        new_markdown = _read_content_input(file_path, content)
        if new_markdown is None:
            sys.stderr.write("Error: Content must be provided via --file, --content, or piped stdin.\n")
            return 1

        res = client.update_page_markdown(
            page_id=page_id,
            markdown=new_markdown,
            allow_delete=allow_delete,
        )

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        normalized = normalize_id(page_id)
        print(f"Page {normalized} markdown updated successfully.")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error updating page {page_id}: {e}\n")
        return 1


def cmd_page_append(
    client: NotionClient,
    page_id: str,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    as_json: bool = False,
) -> int:
    try:
        append_markdown = _read_content_input(file_path, content)
        if append_markdown is None:
            sys.stderr.write("Error: Content must be provided via --file, --content, or piped stdin.\n")
            return 1

        res = client.append_page_markdown(page_id=page_id, markdown=append_markdown)

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        normalized = normalize_id(page_id)
        print(f"Page {normalized} markdown appended successfully.")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error appending to page {page_id}: {e}\n")
        return 1


def cmd_page_replace(
    client: NotionClient,
    page_id: str,
    old_str: str,
    new_str: str,
    replace_all: bool = False,
    as_json: bool = False,
) -> int:
    try:
        res = client.replace_page_markdown_text(
            page_id=page_id,
            old_str=old_str,
            new_str=new_str,
            replace_all=replace_all,
        )

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        normalized = normalize_id(page_id)
        print(f"Page {normalized} replaced '{old_str}' with '{new_str}'.")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error replacing text in page {page_id}: {e}\n")
        return 1


def cmd_page_set_title(
    client: NotionClient,
    page_id: str,
    new_title: str,
    as_json: bool = False,
) -> int:
    try:
        res = client.set_page_title(page_id=page_id, new_title=new_title)

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        normalized = normalize_id(page_id)
        print(f"Page {normalized} title updated to: '{new_title}'")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error updating title for page {page_id}: {e}\n")
        return 1


def cmd_page_delete(
    client: NotionClient,
    page_id: str,
    force: bool = False,
    as_json: bool = False,
) -> int:
    try:
        normalized = normalize_id(page_id)
        if not force and sys.stdin.isatty():
            confirm = input(f"Are you sure you want to move page {normalized} to trash? [y/N]: ")
            if confirm.strip().lower() not in ("y", "yes"):
                print("Aborted.")
                return 0

        res = client.delete_page(page_id=normalized)

        if as_json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return 0

        print(f"Page {normalized} moved to trash successfully.")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error deleting page {page_id}: {e}\n")
        return 1
