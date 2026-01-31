import pandas as pd
from data_engineering.silver_etl import SilverCleaner
import logging
import traceback
from pathlib import Path

logging.basicConfig(level=logging.INFO)

def test_save():
    cleaner = SilverCleaner()
    print("Loading Nvidia...")
    df = cleaner.load_bronze_files("nvidia")
    print(f"Columns: {df.columns.tolist()}")
    print(f"Index: {df.index}")
    
    print("Resetting index...")
    df = df.reset_index(drop=True)
    
    print("Removing dupe cols...")
    df = df.loc[:, ~df.columns.duplicated()]
    
    print("Saving to parquet...")
    try:
        Path("data_engineering/silver").mkdir(parents=True, exist_ok=True)
        df.to_parquet("data_engineering/silver/test_nvidia.parquet", index=False)
        print("Success!")
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    test_save()
