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

if __name__ == "__main__":
    import uvicorn
    # Run dev server
    uvicorn.run(app, host="0.0.0.0", port=8000)
