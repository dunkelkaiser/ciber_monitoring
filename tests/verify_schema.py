import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SchemaVerifier")

SILVER_DIR = Path("data_engineering/silver")

def verify_schema():
    files = ["silver_research_papers.parquet", "silver_vulnerabilities.parquet", "silver_social_signals.parquet"]
    all_passed = True
    
    for f in files:
        path = SILVER_DIR / f
        if not path.exists():
            logger.warning(f"File {f} not found. Skipping.")
            continue
            
        df = pd.read_parquet(path)
        cols = df.columns.tolist()
        logger.info(f"Checking {f}... Cols: {cols}")
        
        # Check for published_date
        if "published_date" not in cols:
            logger.error(f"❌ {f} MISSING 'published_date'")
            all_passed = False
        else:
            logger.info(f"✅ {f} has 'published_date'")
            
        # Check for forbidden columns
        forbidden = ["created_at", "published", "updated", "date"]
        for bad in forbidden:
            if bad in cols:
                logger.error(f"❌ {f} contains forbidden column '{bad}'")
                all_passed = False
                
    if all_passed:
        logger.info("🎉 All schemas verified successfully!")
    else:
        logger.error("⚠️ Schema verification failed.")
        exit(1)

if __name__ == "__main__":
    verify_schema()
