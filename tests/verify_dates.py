
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_engineering.gold_etl import GoldRefiner, GOLD_DIR

def test_dates():
    # Helper to call just the function we want
    refiner = GoldRefiner()
    
    # Run the ETL step
    print("Running create_vulnerability_index...")
    df = refiner.create_vulnerability_index()
    
    if df is None:
        print("SKIP: silver_vulnerabilities missing or empty.")
        return

    # Check Columns
    assert 'event_date' in df.columns, "Missing event_date"
    assert 'asof_date' in df.columns, "Missing asof_date"
    
    # Check Types
    print(f"event_date dtype: {df['event_date'].dtype}")
    print(f"asof_date dtype: {df['asof_date'].dtype}")
    
    # Must be datetime64, not object
    assert pd.api.types.is_datetime64_any_dtype(df['event_date']), "event_date should be datetime"
    assert pd.api.types.is_datetime64_any_dtype(df['asof_date']), "asof_date should be datetime"
    
    # Check contents
    sample = df.iloc[0]
    print(f"Sample row:\n{sample}")
    
    # Verify asof_date is today (or refiner.timestamp)
    expected_asof = pd.to_datetime(refiner.timestamp).floor('D')
    assert sample['asof_date'] == expected_asof, f"Expected asof {expected_asof}, got {sample['asof_date']}"

    print("\nSUCCESS: Date normalization verified.")

if __name__ == "__main__":
    test_dates()
