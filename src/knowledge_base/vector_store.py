# vector_store.py
# outdated
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from typing import List
import os

class VectorStoreManager:
    def __init__(
        self,
        openai_api_key: str,
        persist_dir: str = "./chroma_db",
        collection_name: str = "notion_workspace",
        embedding_model: str = "text-embedding-3-small",  # Cheaper & fast
    ):
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key,
        )
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.vector_store = None

    def build_store(self, documents: List[Document], batch_size: int = 100):
        """
        Create vector store from documents.
        Batches to avoid API rate limits.
        """
        print(f"🔢 Embedding {len(documents)} chunks...")

        # Process in