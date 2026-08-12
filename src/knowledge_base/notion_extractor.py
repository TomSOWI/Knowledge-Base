# notion_extractor.py
from notion_client import Client
from typing import List, Dict, Any
import time

class NotionExtractor:
    def __init__(self, api_key: str):
        self.client = Client(auth=api_key)
        self.pages = []

    def fetch_all_pages(self) -> List[Dict[str, Any]]:
        """
        Uses Notion's search endpoint to retrieve ALL pages 
        and databases in the workspace.
        """
        results = []
        next_cursor = None

        print("🔍 Fetching all Notion pages...")

        while True:
            query_params = {
                "filter": {"value": "page", "property": "object"},
                "page_size": 100,  # Maximum allowed by Notion API
            }
            if next_cursor:
                query_params["start_cursor"] = next_cursor

            response = self.client.search(**query_params)
            results.extend(response.get("results", []))

            # Handle pagination
            if response.get("has_more"):
                next_cursor = response.get("next_cursor")
                time.sleep(0.3)  # Respect Notion API rate limits (3 req/sec)
            else:
                break

        print(f"✅ Found {len(results)} pages")
        self.pages = results
        return results

    def fetch_databases(self) -> List[Dict[str, Any]]:
        """Separately fetch all databases in the workspace."""
        results = []
        next_cursor = None

        while True:
            query_params = {
                "filter": {"value": "database", "property": "object"},
                "page_size": 100,
            }
            if next_cursor:
                query_params["start_cursor"] = next_cursor

            response = self.client.search(**query_params)
            results.extend(response.get("results", []))

            if response.get("has_more"):
                next_cursor = response.get("next_cursor")
                time.sleep(0.3)
            else:
                break

        return results