import os
import time
import logging
from dotenv import load_dotenv

from notion_extractor import NotionExtractor
from notion_parser import NotionParser
from notion_chunker import NotionChunker


from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.faiss import FAISS 

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Load & Validate Config
# ─────────────────────────────────────────────
load_dotenv()

def load_config() -> dict:
    """Load and validate all required environment variables."""
    config = {
        "notion_api_key":  os.getenv("NOTION_API_KEY"),
        "openai_api_key":  os.getenv("OPENAI_API_KEY"),
        "ssl_cert_path":   os.getenv("SSL_CERT_PATH"),
        "faiss_index_path": os.getenv("FAISS_INDEX_PATH", "./faiss_index"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "collection_name": os.getenv("COLLECTION_NAME", "notion_workspace"),
        "chunk_size":      int(os.getenv("CHUNK_SIZE", 1000)),
        "chunk_overlap":   int(os.getenv("CHUNK_OVERLAP", 200)),
        "batch_size":      int(os.getenv("BATCH_SIZE", 50)),
    }

    # Validate required keys
    missing = [k for k in ["notion_api_key", "openai_api_key"]
               if not config.get(k)]
    if missing:
        raise EnvironmentError(
            f"❌ Missing required environment variables: {', '.join(missing)}\n"
            f"   → Check your .env file"
        )

    log.info("✅ Configuration loaded")
    return config


# ─────────────────────────────────────────────
# Step 1: Extract Pages from Notion
# ─────────────────────────────────────────────
def extract_pages(config: dict) -> NotionExtractor:
    """Fetch all pages from Notion workspace."""
    log.info("\n" + "=" * 60)
    log.info("STEP 1: Extracting pages from Notion")
    log.info("=" * 60)

    # Handle optional corporate SSL certificate
    # if config.get("ssl_cert_path") and os.path.exists(config["ssl_cert_path"]):
    #     import httpx
    #     from notion_client import Client
    #     http_client = httpx.Client(verify=config["ssl_cert_path"])
    #     extractor = NotionExtractor.__new__(NotionExtractor)
    #     extractor.client = Client(
    #         auth=config["notion_api_key"],
    #         client=http_client
    #     )
    #     extractor.pages = []
    #     extractor.fetch_all_pages()
    # else:
    extractor = NotionExtractor(config["notion_api_key"])
    extractor.fetch_all_pages()

    log.info(f"✅ Found {len(extractor.pages)} pages")
    return extractor


# ─────────────────────────────────────────────
# Step 2: Parse Page Content
# ─────────────────────────────────────────────
def parse_pages(extractor: NotionExtractor) -> list:
    """Extract text content from every Notion page."""
    log.info("\n" + "=" * 60)
    log.info("STEP 2: Parsing page content")
    log.info("=" * 60)

    parser = NotionParser(extractor.client)
    parsed_pages = []
    total = len(extractor.pages)

    for i, page in enumerate(extractor.pages):
        page_id = page["id"]

        # Safely extract title regardless of property key name
        title = "Untitled"
        for prop_value in page.get("properties", {}).values():
            if prop_value.get("type") == "title":
                title = "".join(
                    t.get("plain_text", "")
                    for t in prop_value.get("title", [])
                )
                break

        log.info(f"  [{i+1}/{total}] Parsing: '{title}'")

        try:
            content = parser.get_page_content(page_id)

            if not content.strip():
                log.warning(f"    ⚠️  Skipping empty page: '{title}'")
                continue

            parsed_pages.append({
                "content": content,
                "metadata": {
                    "page_id":      page_id,
                    "title":        title,
                    "url":          page.get("url", ""),
                    "created_time": page.get("created_time", ""),
                    "last_edited":  page.get("last_edited_time", ""),
                    "parent_type":  page.get("parent", {}).get("type", "unknown"),
                }
            })

        except Exception as e:
            log.error(f"    ❌ Failed to parse '{title}' ({page_id}): {e}")
            continue

    log.info(f"\n✅ Successfully parsed {len(parsed_pages)}/{total} pages")
    return parsed_pages


# ─────────────────────────────────────────────
# Step 3: Chunk Documents
# ─────────────────────────────────────────────
def chunk_pages(parsed_pages: list, config: dict) -> list:
    """Split parsed pages into smaller chunks for embedding."""
    log.info("\n" + "=" * 60)
    log.info("STEP 3: Chunking documents")
    log.info("=" * 60)

    chunker = NotionChunker(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
    )

    chunks = chunker.chunk_documents(parsed_pages)
    log.info(f"✅ Created {len(chunks)} chunks from {len(parsed_pages)} pages")
    return chunks


# ─────────────────────────────────────────────
# Step 4: Embed & Store in FAISS
# ─────────────────────────────────────────────
def embed_and_store(chunks: list, config: dict) -> FAISS:
    """
    Embed document chunks and store in a local FAISS index.
    
    - If an existing index is found at faiss_index_path → load and update it
    - If no index exists yet → create a fresh one
    """
    log.info("\n" + "=" * 60)
    log.info("STEP 4: Embedding & storing in FAISS")
    log.info("=" * 60)

    embeddings = OpenAIEmbeddings(
        model=config["embedding_model"],
        openai_api_key=config["openai_api_key"],
    )

    faiss_path = config["faiss_index_path"]
    batch_size = config["batch_size"]
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    vector_store = None

    # ── Load existing index if available ──────────────
    if os.path.exists(faiss_path):
        log.info(f"📂 Existing FAISS index found at '{faiss_path}' — loading it...")
        try:
            vector_store = FAISS.load_local(
                faiss_path,
                embeddings,
                allow_dangerous_deserialization=True,  # Safe for local files you created
            )
            log.info("✅ Existing index loaded — new chunks will be merged into it")
        except Exception as e:
            log.warning(f"⚠️  Could not load existing index ({e}) — creating fresh index")
            vector_store = None

    # ── Embed in batches ───────────────────────────────
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i: i + batch_size]
        batch_num = (i // batch_size) + 1

        log.info(f"  Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        try:
            if vector_store is None:
                # First batch: create the FAISS index
                vector_store = FAISS.from_documents(
                    documents=batch,
                    embedding=embeddings,
                )
            else:
                # All subsequent batches: merge into existing index
                batch_store = FAISS.from_documents(
                    documents=batch,
                    embedding=embeddings,
                )
                vector_store.merge_from(batch_store)  # FAISS-specific merge

            time.sleep(0.5)  # Avoid OpenAI rate limits

        except Exception as e:
            log.error(f"  ❌ Failed on batch {batch_num}: {e}")
            continue

    # ── Persist index to disk ──────────────────────────
    if vector_store:
        os.makedirs(faiss_path, exist_ok=True)
        vector_store.save_local(faiss_path)
        log.info(f"✅ FAISS index saved to: '{faiss_path}'")
        log.info(f"   Total vectors: {vector_store.index.ntotal}")
    else:
        log.error("❌ No vector store was created — check embedding errors above")

    return vector_store


# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
def print_summary(
    total_pages: int,
    parsed_count: int,
    chunk_count: int,
    vector_store: FAISS,
    start_time: float,
    config: dict,
) -> None:
    duration = time.time() - start_time
    total_vectors = vector_store.index.ntotal if vector_store else 0

    log.info("\n" + "=" * 60)
    log.info("📊 PIPELINE COMPLETE")
    log.info("=" * 60)
    log.info(f"  Pages found:      {total_pages}")
    log.info(f"  Pages parsed:     {parsed_count}")
    log.info(f"  Pages skipped:    {total_pages - parsed_count}")
    log.info(f"  Chunks embedded:  {chunk_count}")
    log.info(f"  Vectors in index: {total_vectors}")
    log.info(f"  Index saved to:   {config['faiss_index_path']}")
    log.info(f"  Duration:         {duration:.1f}s ({duration/60:.1f} min)")
    log.info("=" * 60)


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────
def main():
    start_time = time.time()

    # 1. Load config
    config = load_config()

    # 2. Extract all pages from Notion
    extractor = extract_pages(config)

    # 3. Parse content from each page
    parsed_pages = parse_pages(extractor)

    if not parsed_pages:
        log.error("❌ No pages parsed. Check your Notion integration sharing settings.")
        return

    # 4. Chunk the parsed content
    chunks = chunk_pages(parsed_pages, config)

    if not chunks:
        log.error("❌ No chunks created. Pages may all be empty.")
        return

    # 5. Embed and store in FAISS
    vector_store = embed_and_store(chunks, config)

    # 6. Print summary
    print_summary(
        total_pages=len(extractor.pages),
        parsed_count=len(parsed_pages),
        chunk_count=len(chunks),
        vector_store=vector_store,
        start_time=start_time,
        config=config,
    )


if __name__ == "__main__":
    main()