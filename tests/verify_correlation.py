
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Add project root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from data_engineering.gold_etl import GoldRefiner, GOLD_DIR

def test_correlation_logic():
    refiner = GoldRefiner()
    
    # Mock Risk Data
    # 2 days of risk
    risk_data = {
        'event_date': [
             pd.to_datetime('2024-01-01'), 
             pd.to_datetime('2024-01-02'),
             pd.to_datetime('2024-01-03')
        ],
        'days_risk_score': [100, 200, 50]
    }
    vuln_df = pd.DataFrame(risk_data)
    
    # Mock Social Data
    # 2 days of social (one overlapping, one separate)
    social_data = {
        'text': ['bad terrible', 'good great', 'neutral', 'bad'],
        'created_at': [
            '2024-01-01 10:00:00', # Matches risk
            '2024-01-03 12:00:00', # Matches risk
            '2024-01-04 14:00:00', # No risk data
            '2024-01-01 11:00:00'  # Matches risk (same day)
        ]
    }
    social_df = pd.DataFrame(social_data)
    
    # Run Function to Test
    refiner.create_correlation_matrix(vuln_df, social_df)
    
    # Verify Output
    output_path = GOLD_DIR / "gold_fact_risk_sentiment_daily.parquet"
    if output_path.exists():
        df = pd.read_parquet(output_path)
        print("COLUMNS:" + str(list(df.columns)))
        print("ROWS:" + str(len(df)))
        
        # Check alignment
        # 2024-01-01: Risk 100, Sentiment (bad+bad = neg). df row?
        # 2024-01-02: Risk 200, Sentiment Na/0.
        # 2024-01-03: Risk 50, Sentiment (good = pos).
        # 2024-01-04: Risk Na/0, Sentiment (neutral).
        
        row_01 = df[df['event_date'] == pd.to_datetime('2024-01-01')].iloc[0]
        print(f"2024-01-01: Risk={row_01['days_risk_score_total']}, Sent={row_01['avg_sentiment']}")
        assert row_01['days_risk_score_total'] == 100
        assert row_01['avg_sentiment'] < 0 # Should be negative
        
        row_04 = df[df['event_date'] == pd.to_datetime('2024-01-04')].iloc[0]
        print(f"2024-01-04: Risk={row_04['days_risk_score_total']}, Sent={row_04['avg_sentiment']}")
        assert row_04['days_risk_score_total'] == 0
        
        assert 'run_id' in df.columns
        assert 'asof_date' in df.columns

        print("SUCCESS: Correlation Fact Table verified.")
    else:
        print("FAIL: Output parquet not found.")

if __name__ == "__main__":
    test_correlation_logic()
