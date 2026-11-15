"""Unit tests for notion-cli."""

import unittest
from cli_for_notion.client import normalize_id
from cli_for_notion.commands.db import _format_db_properties
from cli_for_notion.commands.page import _read_content_input


class TestNotionCLI(unittest.TestCase):
    def test_normalize_id_standard_uuid(self):
        uuid_str = "3e76bf4b-dc72-813f-a377-c987fc046733"
        self.assertEqual(normalize_id(uuid_str), uuid_str)

    def test_normalize_id_hex_no_dashes(self):
        raw_hex = "3e76bf4bdc72813fa377c987fc046733"
        expected = "3e76bf4b-dc72-813f-a377-c987fc046733"
        self.assertEqual(normalize_id(raw_hex), expected)

    def test_normalize_id_urls(self):
        urls = [
            "https://notion.so/Page-Title-3e76bf4bdc72813fa377c987fc046733",
            "https://app.notion.com/p/3e76bf4bdc72813fa377c987fc046733",
            "https://app.notion.com/p/3e76bf4bdc72813fa377c987fc046733?pvs=4",
            "https://www.notion.so/workspace/3e76bf4b-dc72-813f-a377-c987fc046733",
        ]
        expected = "3e76bf4b-dc72-813f-a377-c987fc046733"
        for url in urls:
            self.assertEqual(normalize_id(url), expected, f"Failed on URL: {url}")

    def test_format_db_properties(self):
        schema = {
            "Severity": {"type": "select"},
            "Service": {"type": "rich_text"},
            "Status": {"type": "status"},
            "Tags": {"type": "multi_select"},
        }
        raw_props = {
            "Severity": "Critical",
            "Service": "keycloak",
            "Status": "Open",
            "Tags": ["k3s", "security"],
        }
        formatted = _format_db_properties(schema, raw_props)
        self.assertEqual(formatted["Severity"], {"name": "Critical"})
        self.assertEqual(formatted["Service"], [{"text": {"content": "keycloak"}}])
        self.assertEqual(formatted["Status"], {"name": "Open"})
        self.assertEqual(formatted["Tags"], [{"name": "k3s"}, {"name": "security"}])

    def test_read_content_input_escape_sequences(self):
        content = "Line1\\nLine2\\tTabbed"
        res = _read_content_input(None, content)
        self.assertEqual(res, "Line1\nLine2\tTabbed")


if __name__ == "__main__":
    unittest.main()
