from notion_extractor import NotionExtractor
from notion_parser import NotionParser
from chunker import NotionChunker
import os
from dotenv import load_dotenv

load_dotenv()

# ── Setup ──────────────────────────────────────────────
# notion_client_raw = None  # We'll reuse the client from NotionExtractor

extractor = NotionExtractor(os.getenv("NOTION_API_KEY"))
extractor.fetch_all_pages()

# NotionParser needs the same underlying client
parser = NotionParser(extractor.client)  # <-- reuse the same client

# ── Loop Through Pages ─────────────────────────────────
print(f"\nFound {len(extractor.pages)} pages\n")
print("=" * 60)

# Collect all parsed pages
parsed_pages = []

for i, page in enumerate(extractor.pages):
    page_id = page["id"]

    # Safe title extraction
    title = "Untitled"
    for prop_value in page.get("properties", {}).values():
        if prop_value.get("type") == "title":
            title = "".join(
                t.get("plain_text", "") 
                for t in prop_value.get("title", [])
            )
            break

    print(f"[{i+1}/{len(extractor.pages)}] {title}")

    content = parser.get_page_content(page_id)

    if content.strip():
        parsed_pages.append({
            "title":   title,
            "page_id": page_id,
            "url":     page.get("url", ""),
            "content": content,
        })

print(f"\n✅ Successfully parsed {len(parsed_pages)}/{len(extractor.pages)} pages")

# parsed_pages is now ready to pass into your chunker
chunker = NotionChunker()
chunks = chunker.chunk_documents(parsed_pages)