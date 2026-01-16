
import pandas as pd
import sys
import shutil
from pathlib import Path
import uuid

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_engineering.gold_etl import GoldRefiner, GOLD_DIR

def test_gold_append():
    test_name = "gold_test_append"
    test_file = GOLD_DIR / f"{test_name}.parquet"
    
    # Cleanup previous test
    if test_file.exists():
        test_file.unlink()

    print(f"--- Run 1 ---")
    refiner1 = GoldRefiner()
    df1 = pd.DataFrame({
        'id': [1, 2],
        'value': ['a', 'b']
    })
    refiner1.save_gold(df1, test_name, subset=['id'])
    
    # Verify Run 1
    saved_df = pd.read_parquet(test_file)
    print(f"Rows after Run 1: {len(saved_df)}")
    assert len(saved_df) == 2
    assert 'run_id' in saved_df.columns
    assert 'run_ts' in saved_df.columns
    run_id_1 = saved_df['run_id'].iloc[0]
    print(f"Run ID 1: {run_id_1}")

    print(f"\n--- Run 2 (Append) ---")
    refiner2 = GoldRefiner()
    df2 = pd.DataFrame({
        'id': [3, 4], # New IDs
        'value': ['c', 'd']
    })
    refiner2.save_gold(df2, test_name, subset=['id'])
    
    saved_df_2 = pd.read_parquet(test_file)
    print(f"Rows after Run 2: {len(saved_df_2)}")
    assert len(saved_df_2) == 4
    assert len(saved_df_2['run_id'].unique()) == 2
    
    print(f"\n--- Run 3 (Duplicate IDs in input, check dedup within run) ---")
    refiner3 = GoldRefiner()
    df3 = pd.DataFrame({
        'id': [5, 5], # Duplicate ID
        'value': ['e', 'e_dup']
    })
    # dedup by id, keep last -> should keep 'e_dup'
    refiner3.save_gold(df3, test_name, subset=['id']) 
    
    saved_df_3 = pd.read_parquet(test_file)
    print(f"Rows after Run 3: {len(saved_df_3)}")
    # Run 1 (2) + Run 2 (2) + Run 3 (1, deduped) = 5
    assert len(saved_df_3) == 5
    last_row = saved_df_3.iloc[-1]
    assert last_row['value'] == 'e_dup'
    
    print("\nSUCCESS: Gold append and history verified.")

if __name__ == "__main__":
    test_gold_append()
