import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# Create a mock of GoldRefiner logic for testing
def apply_date_logic(df):
    timestamp = datetime.now()
    potential_dates = ['run_ts', 'scraped_date', 'published_date']
    for col in potential_dates:
         if col in df.columns:
             # Force coercion to datetime
             df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
    
    # Initialize with default
    final_date = pd.Series([timestamp.replace(tzinfo=None)] * len(df), index=df.index)
    
    # Cascade
    if 'published_date' in df.columns:
        final_date = df['published_date'].combine_first(final_date)
    if 'scraped_date' in df.columns:
        final_date = df['scraped_date'].combine_first(final_date)
    if 'run_ts' in df.columns:
         final_date = df['run_ts'].combine_first(final_date)
        
    df['final_ts'] = final_date.dt.strftime("%Y-%m-%d")
    return df

def test_fallback_logic():
    print("Testing Date Fallback Priority...")
    
    # Create test scenarios
    data = {
        'title': ['Test1', 'Test2', 'Test3', 'Test4'],
        'run_ts': ['2023-01-01', None, pd.NaT, np.nan], # Sc1: Valid, Sc2-4: Missing
        'scraped_date': [None, '2023-01-02', None, np.nan], # Sc2: Valid
        'published_date': [None, None, '2023-01-03', np.nan] # Sc3: Valid
        # Sc4: All missing -> Should fallback to NOW
    }
    df = pd.DataFrame(data)
    
    print("\nInput Data:")
    print(df)
    
    processed_df = apply_date_logic(df)
    
    print("\nProcessed Data:")
    print(processed_df[['run_ts', 'scraped_date', 'published_date', 'final_ts']])
    
    # Assertions
    # 1. run_ts present
    assert processed_df.loc[0, 'final_ts'] == '2023-01-01', "Failed Priority 1: run_ts"
    # 2. scraped_date fallback
    assert processed_df.loc[1, 'final_ts'] == '2023-01-02', "Failed Priority 2: scraped_date fallback"
    # 3. published_date fallback
    assert processed_df.loc[2, 'final_ts'] == '2023-01-03', "Failed Priority 3: published_date fallback"
    # 4. timestamp fallback (should be today)
    today_str = datetime.now().strftime("%Y-%m-%d")
    assert processed_df.loc[3, 'final_ts'] == today_str, f"Failed Priority 4: timestamp fallback. Expected {today_str}, Got {processed_df.loc[3, 'final_ts']}"
    
    print("\n✅ All logic tests passed!")

if __name__ == "__main__":
    test_fallback_logic()
