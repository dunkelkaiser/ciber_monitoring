
# Power BI Python Script: Storytelling Generator
# Copy this code into a Power Query Python script or reference it.

import pandas as pd
import requests
import json
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path

# --- Configuration ---
# Update this path to valid absolute path on your machine where project resides
PROJECT_ROOT = Path(r"c:\Users\jagua\OneDrive\Documentos\Diplomado IA y TA\Modulo 4  Proyecto Integrador\ciber_monitoring")
GOLD_DIR = PROJECT_ROOT / "data_engineering" / "gold"
RAG_DIR = PROJECT_ROOT / "rag_system"
HISTORY_FILE = GOLD_DIR / "gold_storytelling_history.parquet"
API_URL = "http://localhost:8000/api/v1"
LLM_API_KEY = os.getenv("OPENAI_API_KEY", "") # Or hardcode if secure env

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Storyteller")

# --- Helper Functions ---

def get_api_metric(endpoint):
    """Fetch data from API Gateway."""
    try:
        response = requests.get(f"{API_URL}/{endpoint}", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[-1] # Return latest
            return {}
        return {}
    except Exception as e:
        logger.warning(f"API Fetch Error ({endpoint}): {e}")
        return {}

def get_rag_context(query_text):
    """Query local ChromaDB for context."""
    try:
        # Lazy import to avoid load if not needed or env missing
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        
        chroma_path = RAG_DIR / "chroma_db_store"
        if not chroma_path.exists():
            return "No RAG context available (DB not found)."
            
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        db = Chroma(persist_directory=str(chroma_path), embedding_function=embeddings, collection_name="cyber_intel_collection")
        
        docs = db.similarity_search(query_text, k=3)
        context = "\n".join([f"- {d.page_content[:200]}..." for d in docs])
        return context
    except Exception as e:
        logger.warning(f"RAG Error: {e}")
        return "No RAG context available (Error)."

def generate_llm_insight(risk_idx, innovation_score, context):
    """Generate insight using LLM (OpenAI or Mock)."""
    prompt = f"""
    You are a CISO Assistant.
    Today's Metrics:
    - Tech Edge Score: {innovation_score.get('score', 'N/A')} (Innovation)
    - Vulnerability Index: {risk_idx.get('count', 'N/A')} (Risk Level)
    
    Context from Intelligence:
    {context}
    
    Task: Write a 2-sentence executive summary. 
    Sentence 1: State the current threat/innovation balance.
    Sentence 2: Mention one key driver from context.
    Language: Spanish.
    """
    
    if LLM_API_KEY:
        # Real Call (Simulated for this snippet)
        # response = openai.ChatCompletion.create(...)
        # return response...
        return f"[Generated Insight] El riesgo es alto debido a {risk_idx.get('count')} vulnerabilidades activas. Contexto clave: {context[:50]}..."
    else:
        # Mock Response
        return f"El índice de riesgo ({risk_idx.get('count', 0)}) muestra una tendencia preocupante frente a la innovación ({innovation_score.get('score', 0)}). Se detectan múltiples menciones críticas en papers recientes."

# --- Main Logic ---

def run_storytelling():
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Fetch Data
    risk_data = get_api_metric("vulnerability-index")
    innovation_data = get_api_metric("tech-edge-score")
    
    # 2. RAG Context
    context = get_rag_context("critical vulnerabilities and AI innovation high risk")
    
    # 3. Generate Insight
    insight_text = generate_llm_insight(risk_data, innovation_data, context)
    
    new_entry = {
        "date": today_str,
        "insight": insight_text,
        "risk_value": str(risk_data.get('count', 0)),
        "innovation_value": str(innovation_data.get('score', 0)),
        "run_id": str(uuid.uuid4())
    }
    
    # 4. History Management
    df_history = pd.DataFrame()
    if HISTORY_FILE.exists():
        try:
            df_history = pd.read_parquet(HISTORY_FILE)
        except:
            pass
            
    # Check if today exists to avoid duplicate append on refresh
    if not df_history.empty and 'date' in df_history.columns and today_str in df_history['date'].values:
        logger.info("Insight for today already exists.")
        # Optional: Update it? For now, keep first.
    else:
        # Append
        new_df = pd.DataFrame([new_entry])
        df_history = pd.concat([df_history, new_df], ignore_index=True)
        # Save
        if not GOLD_DIR.exists(): GOLD_DIR.mkdir(parents=True)
        df_history.to_parquet(HISTORY_FILE, index=False)
        
    return df_history

# Execute logic
try:
    insight_history = run_storytelling()
    
    # Create the 'current_insight' dataframe (latest row)
    if not insight_history.empty:
        current_insight = insight_history.tail(1).copy()
    else:
        current_insight = pd.DataFrame(columns=["date", "insight", "risk_value", "innovation_value", "run_id"])
        
    print("Storytelling Script Completed Successfully.")
    print("Dataframes 'insight_history' and 'current_insight' are ready for Power BI.")
    
except Exception as e:
    logger.error(f"Script construction failed: {e}")
    # Fallback for Power BI to not crash
    insight_history = pd.DataFrame()
    current_insight = pd.DataFrame()
