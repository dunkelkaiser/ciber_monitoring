import os
import logging
import pandas as pd
from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import List, Dict, Any

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API_Gateway")

app = FastAPI(
    title="CiberMonitoring Intelligence API",
    description="API Gateway serving Gold Layer insights (Vulnerability Index, Tech Edge Score, Correlations).",
    version="1.0.0"
)

# Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GOLD_DIR = PROJECT_ROOT / "data_engineering" / "gold"

def load_gold_data(file_name: str) -> List[Dict[str, Any]]:
    """Helper to load parquet data from Gold layer."""
    file_path = GOLD_DIR / f"{file_name}.parquet"
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        raise HTTPException(status_code=404, detail=f"Data resource '{file_name}' not found.")
    
    try:
        df = pd.read_parquet(file_path)
        # Handle NaN values for JSON standardization
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error reading {file_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error processing data.")

@app.get("/")
def health_check():
    return {"status": "online", "gold_layer_path": str(GOLD_DIR)}

@app.get("/api/v1/tech-edge-score", tags=["Insights"])
def get_tech_edge_score():
    """Returns the Tech Edge Score (Innovation Ranking)."""
    return load_gold_data("gold_tech_edge_score")

@app.get("/api/v1/tech-edge-score/summary", tags=["Insights"])
def get_tech_edge_summary():
    """Returns the aggregated Tech Edge Score (Daily Average) and Top Paper."""
    try:
        data = load_gold_data("gold_tech_edge_score")
        if not data:
            return {"score": 0, "top_paper": "No data", "paper_count": 0}
            
        df = pd.DataFrame(data)
        
        # Ensure numeric
        if 'tech_edge_total' in df.columns:
            df['tech_edge_total'] = pd.to_numeric(df['tech_edge_total'], errors='coerce')
        else:
             return {"score": 0, "error": "Column tech_edge_total missing"}

        # Filter for latest date (approximate by sorting if date col missing or just take recent N)
        # Using last 50 papers or papers from max run_ts if available
        if 'run_ts' in df.columns:
             df['run_ts'] = pd.to_datetime(df['run_ts'], errors='coerce')
             latest_date = df['run_ts'].max()
             # Filter last 7 days of activity to be robust
             # df_recent = df[df['run_ts'] >= latest_date - pd.Timedelta(days=7)]
             # Actually, let's just take the items from the very last available run_ts
             df_recent = df[df['run_ts'] == latest_date]
        else:
             df_recent = df.tail(50)

        avg_score = df_recent['tech_edge_total'].mean()
        
        # Top paper
        top_paper = df_recent.loc[df_recent['tech_edge_total'].idxmax()] if not df_recent.empty else None
        top_title = top_paper['title'] if top_paper is not None and 'title' in top_paper else "N/A"

        return {
            "score": round(float(avg_score), 2) if pd.notna(avg_score) else 0,
            "top_paper": top_title,
            "paper_count": len(df_recent),
            "date": str(latest_date) if 'run_ts' in df.columns else "Recent"
        }
    except Exception as e:
        logger.error(f"Summary Error: {e}")
        return {"score": 0, "error": str(e)}

@app.get("/api/v1/vulnerability-index", tags=["Insights"])
def get_vulnerability_index():
    """Returns the Vulnerability Index (Time Series)."""
    return load_gold_data("gold_vulnerability_index")

@app.get("/api/v1/correlation/matrix", tags=["Correlations"])
def get_correlation_matrix_data():
    """Returns the Time Series data used for correlation analysis."""
    return load_gold_data("gold_correlation_matrix_data")

@app.get("/api/v1/correlation/values", tags=["Correlations"])
def get_correlation_values():
    """Returns the calculated Correlation Coefficients."""
    return load_gold_data("gold_correlation_values")

@app.get("/api/v1/storytelling-history", tags=["Insights"])
def get_storytelling_history():
    """Returns the full history of AI-generated insights."""
    return load_gold_data("gold_storytelling_history")

if __name__ == "__main__":
    import uvicorn
    # Run dev server
    uvicorn.run(app, host="0.0.0.0", port=8000)
