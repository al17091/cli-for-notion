"""Main CLI entrypoint for notion-cli."""

import argparse
import sys

from notion_cli import __version__
from notion_cli.client import NotionClient
from notion_cli.commands.auth import cmd_auth_set_token, cmd_auth_status
from notion_cli.commands.db import cmd_db_add_item, cmd_db_get, cmd_db_query
from notion_cli.commands.page import (
    cmd_page_append,
    cmd_page_create,
    cmd_page_delete,
    cmd_page_get,
    cmd_page_replace,
    cmd_page_set_title,
    cmd_page_update,
)
from notion_cli.commands.search import cmd_search


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notion",
        description="Fast, reliable Notion CLI for inspecting, reading, and updating Notion pages and databases.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--token", help="Notion API integration token (overrides env and config file)")
    parser.add_argument("--debug", action="store_true", help="Print debug HTTP logs")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # -------------------------------------------------------------
    # auth / whoami
    # -------------------------------------------------------------
    p_whoami = subparsers.add_parser("whoami", help="Check current authentication status")
    p_whoami.add_argument("--json", action="store_true", help="Output raw JSON")

    p_auth = subparsers.add_parser("auth", help="Authentication management")
    auth_sub = p_auth.add_subparsers(dest="auth_action", help="Auth actions")

    p_auth_status = auth_sub.add_parser("status", help="Show current authentication status")
    p_auth_status.add_argument("--json", action="store_true", help="Output raw JSON")

    p_auth_set = auth_sub.add_parser("set-token", help="Save Notion token to ~/.config/notion/config.json")
    p_auth_set.add_argument("token_value", help="Notion API integration token")

    # -------------------------------------------------------------
    # search
    # -------------------------------------------------------------
    p_search = subparsers.add_parser("search", help="Search pages and databases in workspace")
    p_search.add_argument("query", nargs="?", default="", help="Search query string")
    p_search.add_argument("--type", choices=["page", "database"], help="Filter by object type")
    p_search.add_argument("--limit", type=int, default=20, help="Max results to return (default: 20)")
    p_search.add_argument("--json", action="store_true", help="Output raw JSON")

    # -------------------------------------------------------------
    # page
    # -------------------------------------------------------------
    p_page = subparsers.add_parser("page", help="Page operations (read, create, update, append, replace)")
    page_sub = p_page.add_subparsers(dest="page_action", help="Page actions")

    # page get
    p_page_get = page_sub.add_parser("get", help="Retrieve page content as Markdown")
    p_page_get.add_argument("page_id", help="Page UUID or URL")
    p_page_get.add_argument("-o", "--output", help="Write markdown output to file instead of stdout")
    p_page_get.add_argument("--json", action="store_true", help="Output page metadata JSON instead of markdown")
    p_page_get.add_argument("--include-transcript", action="store_true", help="Include meeting note transcripts")

    # page create
    p_page_create = page_sub.add_parser("create", help="Create a new page under a parent page or database")
    p_page_create.add_argument("--parent", required=True, help="Parent page UUID or database UUID")
    p_page_create.add_argument("--title", required=True, help="Page title")
    p_page_create.add_argument("-f", "--file", help="Path to initial markdown file ('-' for stdin)")
    p_page_create.add_argument("-c", "--content", help="Initial markdown content string")
    p_page_create.add_argument("--db", action="store_true", help="Specify if parent is a database")
    p_page_create.add_argument("--json", action="store_true", help="Output created page JSON")

    # page update
    p_page_update = page_sub.add_parser("update", help="Replace page content with new Markdown")
    p_page_update.add_argument("page_id", help="Page UUID or URL")
    p_page_update.add_argument("-f", "--file", help="Path to markdown file ('-' for stdin)")
    p_page_update.add_argument("-c", "--content", help="New markdown content string")
    p_page_update.add_argument("--allow-delete", action="store_true", help="Allow deleting nested child elements")
    p_page_update.add_argument("--json", action="store_true", help="Output response JSON")

    # page append
    p_page_append = page_sub.add_parser("append", help="Append markdown content to the end of a page")
    p_page_append.add_argument("page_id", help="Page UUID or URL")
    p_page_append.add_argument("-f", "--file", help="Path to markdown file ('-' for stdin)")
    p_page_append.add_argument("-c", "--content", help="Markdown content string to append")
    p_page_append.add_argument("--json", action="store_true", help="Output response JSON")

    # page replace
    p_page_replace = page_sub.add_parser("replace", help="Find and replace text in page markdown")
    p_page_replace.add_argument("page_id", help="Page UUID or URL")
    p_page_replace.add_argument("--old", required=True, help="Exact text to replace")
    p_page_replace.add_argument("--new", required=True, help="Replacement text")
    p_page_replace.add_argument("--all", action="store_true", help="Replace all matches (default: first only)")
    p_page_replace.add_argument("--json", action="store_true", help="Output response JSON")

    # page set-title
    p_page_title = page_sub.add_parser("set-title", help="Update page title")
    p_page_title.add_argument("page_id", help="Page UUID or URL")
    p_page_title.add_argument("new_title", help="New title for the page")
    p_page_title.add_argument("--json", action="store_true", help="Output response JSON")

    # page delete
    p_page_del = page_sub.add_parser("delete", help="Move page to trash")
    p_page_del.add_argument("page_id", help="Page UUID or URL")
    p_page_del.add_argument("-f", "--force", action="store_true", help="Skip confirmation prompt")
    p_page_del.add_argument("--json", action="store_true", help="Output response JSON")

    # -------------------------------------------------------------
    # db
    # -------------------------------------------------------------
    p_db = subparsers.add_parser("db", help="Database operations (get, query, add-item)")
    db_sub = p_db.add_subparsers(dest="db_action", help="Database actions")

    # db get
    p_db_get = db_sub.add_parser("get", help="Get database details and schema")
    p_db_get.add_argument("database_id", help="Database UUID or URL")
    p_db_get.add_argument("--json", action="store_true", help="Output raw JSON")

    # db query
    p_db_query = db_sub.add_parser("query", help="Query items in database")
    p_db_query.add_argument("database_id", help="Database UUID or URL")
    p_db_query.add_argument("--filter", dest="filter_json", help="Filter criteria JSON string")
    p_db_query.add_argument("--sorts", dest="sorts_json", help="Sort criteria JSON string")
    p_db_query.add_argument("--limit", type=int, default=50, help="Max items to retrieve (default: 50)")
    p_db_query.add_argument("--json", action="store_true", help="Output raw JSON")

    # db add-item
    p_db_add = db_sub.add_parser("add-item", help="Add an entry to a database")
    p_db_add.add_argument("database_id", help="Database UUID or URL")
    p_db_add.add_argument("--title", required=True, help="Item title")
    p_db_add.add_argument("--props", dest="props_json", help="Additional properties JSON string")
    p_db_add.add_argument("--json", action="store_true", help="Output raw JSON")

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Handle auth set-token before creating client (as it doesn't require an existing token)
    if args.command == "auth" and args.auth_action == "set-token":
        return cmd_auth_set_token(args.token_value)

    # Initialize client for all other commands
    try:
        client = NotionClient(token=args.token, debug=args.debug)
    except Exception as e:
        sys.stderr.write(f"Configuration error: {e}\n")
        return 1

    # Route commands
    if args.command == "whoami":
        return cmd_auth_status(client, as_json=args.json)

    if args.command == "auth":
        if args.auth_action == "status" or not args.auth_action:
            return cmd_auth_status(client, as_json=getattr(args, "json", False))
        parser.print_help()
        return 1

    if args.command == "search":
        return cmd_search(
            client=client,
            query=args.query,
            filter_type=args.type,
            limit=args.limit,
            as_json=args.json,
        )

    if args.command == "page":
        if not args.page_action:
            parser.parse_args(["page", "--help"])
            return 0
        if args.page_action == "get":
            return cmd_page_get(
                client=client,
                page_id=args.page_id,
                output_path=args.output,
                as_json=args.json,
                include_transcript=args.include_transcript,
            )
        if args.page_action == "create":
            return cmd_page_create(
                client=client,
                parent_id=args.parent,
                title=args.title,
                file_path=args.file,
                content=args.content,
                is_parent_db=args.db,
                as_json=args.json,
            )
        if args.page_action == "update":
            return cmd_page_update(
                client=client,
                page_id=args.page_id,
                file_path=args.file,
                content=args.content,
                allow_delete=args.allow_delete,
                as_json=args.json,
            )
        if args.page_action == "append":
            return cmd_page_append(
                client=client,
                page_id=args.page_id,
                file_path=args.file,
                content=args.content,
                as_json=args.json,
            )
        if args.page_action == "replace":
            return cmd_page_replace(
                client=client,
                page_id=args.page_id,
                old_str=args.old,
                new_str=args.new,
                replace_all=args.all,
                as_json=args.json,
            )
        if args.page_action == "set-title":
            return cmd_page_set_title(
                client=client,
                page_id=args.page_id,
                new_title=args.new_title,
                as_json=args.json,
            )
        if args.page_action == "delete":
            return cmd_page_delete(
                client=client,
                page_id=args.page_id,
                force=args.force,
                as_json=args.json,
            )

    if args.command == "db":
        if not args.db_action:
            parser.parse_args(["db", "--help"])
            return 0
        if args.db_action == "get":
            return cmd_db_get(
                client=client,
                database_id=args.database_id,
                as_json=args.json,
            )
        if args.db_action == "query":
            return cmd_db_query(
                client=client,
                database_id=args.database_id,
                filter_json=args.filter_json,
                sorts_json=args.sorts_json,
                limit=args.limit,
                as_json=args.json,
            )
        if args.db_action == "add-item":
            return cmd_db_add_item(
                client=client,
                database_id=args.database_id,
                title=args.title,
                props_json=args.props_json,
                as_json=args.json,
            )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
