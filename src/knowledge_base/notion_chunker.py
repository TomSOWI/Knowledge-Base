from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict
from langchain_core.documents import Document
#from langchain.schema import Document
#from langchain.docstore.document import Document


class NotionChunker:
    def __init__(
        self,
        chunk_size: int = 1000,      # Characters per chunk
        chunk_overlap: int = 200,     # Overlap to preserve context
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Split priority: paragraphs → sentences → words → chars
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def chunk_documents(
        self,
        pages_content: List[Dict]  # [{"content": str, "metadata": dict}]
    ) -> List[Document]:
        """Split all pages into LangChain Document chunks with metadata."""
        all_chunks = []

        for page in pages_content:
            content = page.get("content", "").strip()
            metadata = page.get("metadata", {})

            if not content:
                continue  # Skip empty pages

            chunks = self.splitter.split_text(content)

            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "source": f"notion:{metadata.get('page_id', 'unknown')}",
                    }
                )
                all_chunks.append(doc)

        print(f"📄 Created {len(all_chunks)} chunks from {len(pages_content)} pages")
        return all_chunks