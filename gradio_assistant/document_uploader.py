import os
import logging
import fitz  # PyMuPDF
import pandas as pd
import json
from pathlib import Path
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DocUploader")

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
CHROMA_PATH = PROJECT_ROOT / "rag_system" / "chroma_db_store"
class DocumentProcessor:
    def __init__(self):
        self.embeddings_model = None
        self.vector_store = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def _init_resources(self):
        if not self.embeddings_model:
            self.embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        if not self.vector_store:
            self.vector_store = Chroma(
                collection_name="cyber_intel_collection",
                embedding_function=self.embeddings_model,
                persist_directory=str(CHROMA_PATH)
            )

    def process_file(self, file_path: str) -> str:
        """Reads file, chunks it, and adds to Vector DB."""
        # Lazy Init
        try:
            self._init_resources()
        except Exception as e:
            return f"❌ Database Init Error: {e}"

        if not file_path:
            return "No file provided."

        path_obj = Path(file_path)
        ext = path_obj.suffix.lower()
        
        try:
            text_content = ""
            metadata = {"source": path_obj.name, "type": ext}

            if ext == ".pdf":
                doc = fitz.open(file_path)
                for page in doc:
                    text_content += page.get_text() + "\n"
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            elif ext == ".csv":
                df = pd.read_csv(file_path)
                text_content = df.to_string()
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    text_content = json.dumps(data, indent=2)
            else:
                return f"Unsupported file type: {ext}"

            if not text_content.strip():
                return "File is empty or text could not be extracted."

            # Create Document
            doc_obj = Document(page_content=text_content, metadata=metadata)
            
            # Split
            splits = self.text_splitter.split_documents([doc_obj])
            
            # Embed & Store
            if splits:
                self.vector_store.add_documents(documents=splits)
                return f"✅ Successfully ingested '{path_obj.name}'. Added {len(splits)} chunks to Knowledge Base."
            else:
                return "No content chunks created."

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return f"❌ Error processing file: {str(e)}"
