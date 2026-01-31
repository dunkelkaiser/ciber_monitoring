import pandas as pd
from data_engineering.silver_etl import SilverCleaner
import logging

logging.basicConfig(level=logging.INFO)

def debug_columns():
    cleaner = SilverCleaner()
    
    print("--- Loading NVIDIA ---")
    nvidia = cleaner.load_bronze_files("nvidia")
    print(f"Cols: {nvidia.columns.tolist()}")
    print(f"Unique? {nvidia.columns.is_unique}")

    print("--- Loading OpenAI ---")
    openai_df = cleaner.load_bronze_files("openai")
    print(f"Cols: {openai_df.columns.tolist()}")

    print("--- Loading ArXiv ---")
    arxiv = cleaner.load_bronze_files("arxiv")
    print(f"Cols: {arxiv.columns.tolist()}")
    print(f"Unique? {arxiv.columns.is_unique}")
    
    # Simulate rename
    if not arxiv.empty:
         if 'published' in arxiv.columns:
             arxiv.rename(columns={'published': 'published_date'}, inplace=True)
         print(f"Arxiv after rename Cols: {arxiv.columns.tolist()}")
         print(f"Unique? {arxiv.columns.is_unique}")

if __name__ == "__main__":
    debug_columns()
