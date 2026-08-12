from notion_client import Client
from typing import List, Dict, Any, Optional
import time

class NotionParser:
    def __init__(self, client: Client):
        self.client = client

    def get_page_content(self, page_id: str) -> str:
        """Recursively extract all text content from a Notion page."""
        blocks = self._fetch_blocks(page_id)
        return self._parse_blocks(blocks)

    def _fetch_blocks(self, block_id: str) -> List[Dict]:
        """Fetch all blocks for a given page/block ID with pagination."""
        all_blocks = []
        next_cursor = None

        while True:
            params = {"block_id": block_id, "page_size": 100}
            if next_cursor:
                params["start_cursor"] = next_cursor

            response = self.client.blocks.children.list(**params)
            all_blocks.extend(response.get("results", []))

            if response.get("has_more"):
                next_cursor = response.get("next_cursor")
                time.sleep(0.3)
            else:
                break

        return all_blocks

    def _parse_blocks(self, blocks: List[Dict], depth: int = 0) -> str:
        """Convert Notion blocks to clean plain text."""
        text_parts = []
        indent = "  " * depth  # Visual indentation for nested content

        for block in blocks:
            block_type = block.get("type")
            block_data = block.get(block_type, {})
            text = ""

            # --- Text-based blocks ---
            if block_type in [
                "paragraph", "quote", "callout",
                "bulleted_list_item", "numbered_list_item", "to_do"
            ]:
                text = self._extract_rich_text(block_data.get("rich_text", []))
                if block_type == "to_do":
                    checked = "✅" if block_data.get("checked") else "⬜"
                    text = f"{checked} {text}"

            # --- Heading blocks ---
            elif block_type in ["heading_1", "heading_2", "heading_3"]:
                level = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}
                text = f"{level[block_type]} {self._extract_rich_text(block_data.get('rich_text', []))}"

            # --- Code blocks ---
            elif block_type == "code":
                lang = block_data.get("language", "")
                code = self._extract_rich_text(block_data.get("rich_text", []))
                text = f"```{lang}\n{code}\n```"

            # --- Table of contents, dividers ---
            elif block_type == "divider":
                text = "---"

            # --- Embed/bookmark ---
            elif block_type in ["bookmark", "embed"]:
                url = block_data.get("url", "")
                text = f"[Link: {url}]"

            # --- Child pages ---
            elif block_type == "child_page":
                title = block_data.get("title", "Untitled")
                text = f"[Child Page: {title}]"

            if text:
                text_parts.append(f"{indent}{text}")

            # --- Recurse into children if they exist ---
            if block.get("has_children") and block_type != "child_page":
                child_blocks = self._fetch_blocks(block["id"])
                child_text = self._parse_blocks(child_blocks, depth + 1)
                if child_text:
                    text_parts.append(child_text)

        return "\n".join(text_parts)

    def _extract_rich_text(self, rich_text: List[Dict]) -> str:
        """Flatten Notion's rich_text array into a plain string."""
        return "".join([rt.get("plain_text", "") for rt in rich_text])

    def get_page_metadata(self, page: Dict) -> Dict:
        """Extract useful metadata from a page object."""
        # Extract title (varies by page type)
        title = "Untitled"
        props = page.get("properties", {})

        for prop_name, prop_value in props.items():
            if prop_value.get("type") == "title":
                title_parts = prop_value.get("title", [])
                title = "".join([t.get("plain_text", "") for t in title_parts])
                break

        return {
            "page_id": page["id"],
            "title": title,
            "url": page.get("url", ""),
            "created_time": page.get("created_time", ""),
            "last_edited_time": page.get("last_edited_time", ""),
            "parent_type": page.get("parent", {}).get("type", ""),
        }