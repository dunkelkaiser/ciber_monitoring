
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

# API Keys (Loaded from environment or hardcoded safe storage)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "") 
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Model Config
MODELS = {
    "gemini": "gemini-3-flash-preview",
    "openai": "gpt-5-nano-2025-08-07",
    "claude": "claude-haiku-4-5-20251001"
}

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Storyteller")

# --- Helper Functions ---

def get_api_metric(endpoint):
    """Fetch data from API Gateway."""
    try:
        response = requests.get(f"{API_URL}/{endpoint}", timeout=5)
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

# --- LLM API Calls ---

def call_gemini(prompt, model):
    """Call Google Gemini API."""
    if not GOOGLE_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()['candidates'][0]['content']['parts'][0]['text']
        logger.warning(f"Gemini Error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"Gemini Exception: {e}")
    return None

def call_openai(prompt, model):
    """Call OpenAI API."""
    if not OPENAI_API_KEY: return None
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        logger.warning(f"OpenAI Error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"OpenAI Exception: {e}")
    return None

def call_claude(prompt, model):
    """Call Anthropic Claude API."""
    if not ANTHROPIC_API_KEY: return None
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return resp.json()['content'][0]['text']
        logger.warning(f"Claude Error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.warning(f"Claude Exception: {e}")
    return None

def generate_insight_with_fallback(risk_idx, innovation_score, context):
    """Generate insight using Multi-Model Fallback: Gemini -> OpenAI -> Claude."""
    
    prompt = f"""
    You are a CISO Assistant specialized in technology risk and emerging innovation analysis.

    Current Indicators (Tech Edge Context):
    - Tech Edge Score: {innovation_score.get('score', 'N/A')}
    Represents the organization's current position relative to the technological frontier 
    (innovation velocity, adoption of emerging technologies, and competitive differentiation).

    - Vulnerability Index: {risk_idx.get('count', 'N/A')}
    Represents the current exposure level to known and emerging cyber threats, vulnerabilities, 
    and systemic risks associated with operating near the technological edge.

    Contextual Signals:
    {context}

    Task:
    Write a concise executive analysis in Spanish (2–3 sentences) that:
    1. Explains what the current levels of both indices mean in terms of operating at the technological edge 
    (balance between innovation momentum and risk exposure).
    2. Interprets whether the organization is in a position of controlled innovation, emerging risk tension, 
    or critical imbalance.
    3. Highlights the most relevant driver or signal from the provided context that explains the current state.

    Output requirements:
    - Plain text only.
    - No LaTeX, no Markdown, no bullet points, no emojis.
    - No titles, labels, or decorative formatting.
    - Write as a continuous executive narrative suitable for dashboards or automated reports.

    Tone: strategic, interpretative, and suitable for executive decision-making.
    """
    
    # 1. Gemini
    logger.info(f"Attempting Gemini ({MODELS['gemini']})...")
    result = call_gemini(prompt, MODELS['gemini'])
    if result: return (f"[Gemini] {result}", MODELS['gemini'])
    
    # 2. OpenAI
    logger.info(f"Fallback to OpenAI ({MODELS['openai']})...")
    result = call_openai(prompt, MODELS['openai'])
    if result: return (f"[OpenAI] {result}", MODELS['openai'])
    
    # 3. Claude
    logger.info(f"Fallback to Claude ({MODELS['claude']})...")
    result = call_claude(prompt, MODELS['claude'])
    if result: return (f"[Claude] {result}", MODELS['claude'])
    
    # Final Fallback
    return ("No se pudo generar el insight con nungún modelo (APIs fallaron o no disponibles).", "None")

# --- Main Logic ---

def run_storytelling():
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Fetch Data
    risk_data = get_api_metric("vulnerability-index")
    innovation_data = get_api_metric("tech-edge-score")
    
    # 2. RAG Context
    context = get_rag_context("critical vulnerabilities and AI innovation high risk")
    
    # 3. Generate Insight (Multi-Model)
    insight_text, model_used = generate_insight_with_fallback(risk_data, innovation_data, context)
    
    new_entry = {
        "date": today_str,
        "insight": insight_text,
        "model_used": model_used,
        "risk_value": str(risk_data.get('count', 0)),
        "innovation_value": str(innovation_data.get('score', 0)),
        "run_id": str(uuid.uuid4())
    }
    
    # 4. History Management (Load -> Append -> Save -> Return ONLY Today)
    df_history = pd.DataFrame()
    if HISTORY_FILE.exists():
        try:
            df_history = pd.read_parquet(HISTORY_FILE)
        except:
            pass
            
    # Deduplicate: If today exists, drop it and append new (or keep old? defaulting to replace for latest insight)
    if not df_history.empty and 'date' in df_history.columns:
        df_history = df_history[df_history['date'] != today_str]
        
    # Append
    new_df = pd.DataFrame([new_entry])
    df_history = pd.concat([df_history, new_df], ignore_index=True)
    
    # Save Full History to Gold
    if not GOLD_DIR.exists(): GOLD_DIR.mkdir(parents=True)
    df_history.to_parquet(HISTORY_FILE, index=False)
    
    # Return Only Today's Insight for Power BI Step
    return new_df

# Execute logic
try:
    # Power BI expects a dataframe output
    current_insight_df = run_storytelling()
    
    # For Power BI "Python Script" visual/transform:
    # It scans for dataframes. We expose 'current_insight_df'.
    # Note: 'insight_history' is saved to disk, but not exposed to avoid giant memory load in this specific query step if not needed.
    
    print("Storytelling Generated:", current_insight_df.iloc[0]['insight'])
    print("Model Used:", current_insight_df.iloc[0]['model_used'])
    
except Exception as e:
    logger.error(f"Script failed: {e}")
    current_insight_df = pd.DataFrame({"Error": [str(e)]})
