import os
import logging
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# LangChain imports (The simpler "Stack")
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DataFrameLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("RAG_Ingest")

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
SILVER_DIR = PROJECT_ROOT / "data_engineering" / "silver"
CHROMA_PATH = BASE_DIR / "chroma_db_store"

def run_ingestion():
    if not SILVER_DIR.exists():
        logger.error(f"Silver directory not found at {SILVER_DIR}")
        return

    # 1. Initialize Embeddings (Sentence Transformers - Local & Free)
    # Using 'all-MiniLM-L6-v2' (Small, Fast, Good for RAG)
    logger.info("Initializing Embeddings Model (all-MiniLM-L6-v2)...")
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 2. Initialize ChromaDB (Persistent)
    logger.info(f"Initializing Vector Store at {CHROMA_PATH}...")
    try:
        vector_store = Chroma(
            collection_name="cyber_intel_collection",
            embedding_function=embeddings_model,
            persist_directory=str(CHROMA_PATH)
        )
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        if "compaction" in str(e).lower() or "internal" in str(e).lower():
            logger.warning("Corrupted database detected. Deleting and recreating...")
            import shutil
            if CHROMA_PATH.exists():
                shutil.rmtree(CHROMA_PATH)
            vector_store = Chroma(
                collection_name="cyber_intel_collection",
                embedding_function=embeddings_model,
                persist_directory=str(CHROMA_PATH)
            )
        else:
            raise e

    # 3. Load & Process Datasets
    # We load Silver data because it has the raw text content needed for context.
    
    datasets_to_ingest = [
        {
            "name": "silver_vulnerabilities",
            "text_column": "description", # Assuming description exists
            "metadata_cols": ["cve_id", "source_entity", "published_date"] # Adjust based on schema
        },
        {
            "name": "silver_research_papers",
            "text_column": "title", # Title is the main text here. 
            "metadata_cols": ["link", "source_entity"]
        },
        {
            "name": "silver_social_signals",
            "text_column": "text", 
            "metadata_cols": ["id", "created_at"]
        }
    ]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    all_docs = []

    for ds in datasets_to_ingest:
        parquet_path = SILVER_DIR / f"{ds['name']}.parquet"
        if not parquet_path.exists():
            logger.warning(f"Dataset {ds['name']} not found. Skipping.")
            continue
        
        logger.info(f"Processing {ds['name']}...")
        df = pd.read_parquet(parquet_path)
        
        # Ensure text column exists and is string
        if ds['text_column'] not in df.columns:
            logger.warning(f"Column {ds['text_column']} missing in {ds['name']}. Available: {df.columns}")
            continue
            
        df[ds['text_column']] = df[ds['text_column']].fillna("").astype(str)
        
        # Construct simplified metadata dicts
        # We assume columns exist, if not fillna
        for col in ds['metadata_cols']:
            if col not in df.columns:
                df[col] = "UNKNOWN"
            else:
                df[col] = df[col].astype(str)

        # Convert to Documents
        # DataFrameLoader is okay, but manual creation gives more control over content_page
        for _, row in tqdm(df.iterrows(), total=len(df), desc=f"Loading {ds['name']}"):
            content = row[ds['text_column']]
            if len(content) < 10: continue # Skip noise
            
            metadata = {col: row[col] for col in ds['metadata_cols']}
            metadata['source_dataset'] = ds['name']
            
            doc = Document(page_content=content, metadata=metadata)
            all_docs.append(doc)

    logger.info(f"Total Documents prepared: {len(all_docs)}")

    # 4. Spitting
    logger.info("Splitting documents...")
    splits = text_splitter.split_documents(all_docs)
    logger.info(f"Created {len(splits)} chunks.")

    # 5. Indexing (Batch upsert)
    # Chroma handles batching, but for safety with large datasets we can loop
    if splits:
        batch_size = 100
        for i in tqdm(range(0, len(splits), batch_size), desc="Indexing Chunks"):
            batch = splits[i:i + batch_size]
            try:
                vector_store.add_documents(documents=batch)
            except Exception as e:
                logger.error(f"Error adding batch to ChromaDB: {e}")
                if "compaction" in str(e).lower() or "internal" in str(e).lower():
                    logger.warning("Internal ChromaDB error during indexing. Aborting batch and suggesting reset.")
                    # We could auto-reset here, but it's dangerous mid-loop. 
                    # For now, just raise and let the user know, or we can try to re-init.
                    raise e
                else:
                    raise e
            
        logger.info("✅ Vector Database Successfully Updated!")
    else:
        logger.warning("No new content to index.")

if __name__ == "__main__":
    run_ingestion()
