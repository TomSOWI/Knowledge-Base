import os
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# Validate keys exist
assert NOTION_API_KEY, "Missing NOTION_API_KEY"
assert OPENAI_API_KEY, "Missing OPENAI_API_KEY"