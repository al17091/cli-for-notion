# cli-for-notion

A blazing-fast, lightweight, zero-dependency command-line interface (CLI) for Notion, built exclusively with the Python standard library.

Designed for developers, system administrators, and AI coding agents who need a streamlined, scriptable way to read, create, update, and search Notion pages and databases without the heavyweight overhead of Model Context Protocol (MCP) servers or bulky client libraries.

> [!IMPORTANT]
> **Disclaimer**: `cli-for-notion` is an independent, unofficial open-source project and is not affiliated with, endorsed by, or sponsored by Notion Labs, Inc. "Notion" is a registered trademark of Notion Labs, Inc.

---

## Key Features

- **Zero External Dependencies**: Built entirely on Python 3.9+ standard library (`urllib.request`). No `pip install` dependency conflicts, virtualenv requirements, or runtime bloat.
- **Native Markdown Support**: Direct support for the Notion API (2026-03-11) markdown endpoints (`/v1/pages/{id}/markdown`). Retrieve, overwrite, append, or perform targeted find-and-replace on page markdown without dealing with nested Notion block objects.
- **Unix Pipeline & Stdin Friendly**: Seamlessly pipe markdown content into commands (`cat doc.md | notion page update <PAGE_ID>`).
- **Smart URL & UUID Normalization**: Accepts Notion browser URLs (`https://app.notion.com/p/...`), 32-character hex strings, or standard dashed UUIDs interchangeably.
- **Database & Data Source Auto-Resolution**: Transparently bridges Notion 2026 Database and Data Source structures, automatically formatting common property types (`select`, `rich_text`, `status`, `multi_select`).
- **Resilient**: Automatic rate limit detection (HTTP 429) with exponential backoff and `Retry-After` header adherence.

---

## Installation

### Standard Installation (via Git)

You can install `cli-for-notion` directly from GitHub using `pip`, `pipx`, or `uv` without manually cloning the repository:

```bash
# Using pip
pip install git+https://github.com/al17091/cli-for-notion.git

# Or isolated via pipx (recommended for global CLI tools)
pipx install git+https://github.com/al17091/cli-for-notion.git

# Or using uv
uv tool install git+https://github.com/al17091/cli-for-notion.git
```

This installs `notion`, `ntn`, and `cli-for-notion` commands directly into your PATH.

---

### Local Development / Hacking

If you are developing or customizing `cli-for-notion` locally:

```bash
git clone git@github.com:al17091/cli-for-notion.git
cd cli-for-notion
pip install -e .
```

---

## Authentication

Obtain an internal integration token (`ntn_...` or `secret_...`) from [Notion Developers - My Integrations](https://www.notion.so/profile/integrations).

### 1. Configure Token via CLI
Save the token securely to `~/.config/notion/config.json` with strict `0600` file permissions:

```bash
notion auth set-token "ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 2. Configure via Environment Variable (Alternative)
Alternatively, export the token in your shell environment:

```bash
export NOTION_API_KEY="ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# or
export NOTION_TOKEN="ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 3. Verify Connection
```bash
notion whoami
# or
ntn whoami
```

Output:
```text
Authenticated as: lab_enhance (ce00ee66-8ac5-460c-b5b4-4c7277f4d592)
Workspace:        Engineering Hub
Status:           Active (Valid token)
```

---

## Usage Guide

You can use either `notion` or `ntn` interchangeably.

### 1. Page Operations (`notion page`)

#### Retrieve Page Markdown (`get`)
```bash
# Print markdown directly to stdout
notion page get <PAGE_ID_OR_URL>

# Save markdown output directly to a file
notion page get <PAGE_ID_OR_URL> -o document.md

# Retrieve page metadata JSON instead of markdown
notion page get <PAGE_ID_OR_URL> --json
```

#### Create a Page (`create`)
```bash
# Create an empty page under a parent page or database
notion page create --parent <PARENT_ID> --title "Incident Postmortem"

# Create and populate immediately from a markdown file
notion page create --parent <PARENT_ID> --title "Weekly Report" -f report.md

# Create using inline markdown content
notion page create --parent <PARENT_ID> --title "Tasks" -c "## Action Items\n- [ ] Deploy v2.0\n- [ ] Update DNS"

# Pipe markdown from stdin
cat notes.md | notion page create --parent <PARENT_ID> --title "Notes" -f -
```

#### Update Page Markdown Content (`update`)
Replaces the entire content body of the target page:

```bash
# Overwrite page body from a local markdown file
notion page update <PAGE_ID_OR_URL> -f updated.md

# Overwrite page body via piped input
echo -e "## Updated Section\nNew verified metrics." | notion page update <PAGE_ID_OR_URL>

# Allow deletion of nested child pages/databases if not present in the new content
notion page update <PAGE_ID_OR_URL> -f clean.md --allow-delete
```

#### Append Markdown to Page (`append`)
Appends content at the end of the page without modifying existing content:

```bash
# Append an inline string
notion page append <PAGE_ID_OR_URL> -c "\n### Appendices\n- Verified on node-01."

# Append content from a file
notion page append <PAGE_ID_OR_URL> -f additions.md
```

#### Targeted Find-and-Replace (`replace`)
Perform precise text replacements in page markdown (safely preserves parent page layouts, inline databases, and child links):

```bash
# Replace first match
notion page replace <PAGE_ID_OR_URL> --old "Status: Draft" --new "Status: Approved"

# Replace all occurrences
notion page replace <PAGE_ID_OR_URL> --old "TODO" --new "DONE" --all
```

#### Change Page Title (`set-title`)
```bash
notion page set-title <PAGE_ID_OR_URL> "New Architecture Design (Final)"
```

#### Delete / Trash Page (`delete`)
```bash
notion page delete <PAGE_ID_OR_URL> --force
```

---

### 2. Database Operations (`notion db`)

#### Inspect Database Schema (`get`)
```bash
notion db get <DATABASE_ID_OR_URL>
```

#### Query Database Items (`query`)
```bash
# List recent items
notion db query <DATABASE_ID_OR_URL> --limit 20

# Query with JSON filter
notion db query <DATABASE_ID_OR_URL> \
  --filter '{"property": "Severity", "select": {"equals": "Critical"}}'

# Output full JSON results
notion db query <DATABASE_ID_OR_URL> --json
```

#### Add Item to Database (`add-item`)
Properties are automatically mapped and typed (`select`, `rich_text`, `status`, etc.):

```bash
# Add basic entry
notion db add-item <DATABASE_ID_OR_URL> --title "[Alert] API Latency Spike"

# Add entry with custom properties
notion db add-item <DATABASE_ID_OR_URL> \
  --title "[Alert] Keycloak Service Degraded" \
  --props '{"Severity": "Critical", "Service": "auth-gateway", "Status": "Open"}'
```

---

### 3. Workspace Search (`notion search`)

```bash
# Search everything by keyword
notion search "Infrastructure"

# Restrict search to pages only
notion search "Kubernetes" --type page

# Restrict search to databases only
notion search "Alerts" --type database
```

---

## Token Precedence

The integration token is resolved in the following priority:
1. Explicit CLI argument: `--token <TOKEN>`
2. Environment variables: `NOTION_API_KEY` or `NOTION_TOKEN`
3. Configuration file: `~/.config/notion/config.json`

---

## Development & Testing

Run the built-in unit tests with Python's standard `unittest` test runner:

```bash
python3 -m unittest discover -s tests
```

---

## License

This project is licensed under the [MIT License](LICENSE).
