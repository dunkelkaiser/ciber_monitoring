import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MinMaxScaler
import statsmodels.api as sm

# Optional API imports
try:
    import openai
    from anthropic import Anthropic
    import google.generativeai as genai
except ImportError:
    pass

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("GoldETL")

# Paths
BASE_DIR = Path(__file__).resolve().parent
SILVER_DIR = BASE_DIR / "silver"
GOLD_DIR = BASE_DIR / "gold"

GOLD_DIR.mkdir(parents=True, exist_ok=True)

class GoldRefiner:
    def __init__(self):
        self.timestamp = datetime.now()
        # API Clients initialization (Placeholders)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY")

        if self.openai_key:
            openai.api_key = self.openai_key
            logger.info("OpenAI Client Initialized")

    def load_silver(self, name: str) -> pd.DataFrame:
        path = SILVER_DIR / f"{name}.parquet"
        if not path.exists():
            logger.warning(f"Silver dataset {name} not found.")
            return pd.DataFrame()
        return pd.read_parquet(path)

    def save_gold(self, df: pd.DataFrame, name: str):
        if df.empty:
            logger.warning(f"DataFrame for {name} is empty. Skipping gold save.")
            return

        output_path = GOLD_DIR / f"{name}.parquet"
        
        # Convert objects to string for Parquet safety
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str)
                
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved Gold Dataset: {name} ({len(df)} rows)")
        
        # Simulating SQL Export
        sql_name = name.replace("gold_", "")
        logger.info(f"[SQL Bridge] Data ready for loading into PostgreSQL table '{sql_name}'.")

    # --- 1. Vulnerability Index (Time Series) ---
    def create_vulnerability_index(self):
        logger.info("Building Vulnerability Index...")
        df = self.load_silver("silver_vulnerabilities")
        if df.empty: return

        # Simulation: If published_date is missing or UNKNOWN, assign simulated recent dates
        # for time-series demo.
        if 'published_date' not in df.columns or df['published_date'].iloc[0] == "UNKNOWN":
            logger.info("Simulating historical dates for Time Series Analysis...")
            # Distribute items over last 30 days
            dates = [self.timestamp - timedelta(days=x % 30) for x in range(len(df))]
            df['date'] = dates
        else:
            df['date'] = pd.to_datetime(df['published_date'], errors='coerce').fillna(self.timestamp)
        
        df['date'] = pd.to_datetime(df['date']).dt.date
        
        # Aggregation: Count per day per source
        daily_counts = df.groupby(['date', 'source_entity']).size().reset_index(name='count')
        
        # Risk Severity Weighting (Simulation logic if severity is missing)
        # If we had 'severity' col "HIGH", "CRITICAL"...
        # We assume flat weight for now or random
        daily_counts['days_risk_score'] = daily_counts['count'] * 10 # Base score
        
        # Advanced: Rolling Average (Time Series Feature)
        daily_counts = daily_counts.sort_values('date')
        daily_counts['risk_moving_avg_7d'] = daily_counts.groupby('source_entity')['days_risk_score'].transform(lambda x: x.rolling(7, min_periods=1).mean())
        
        # Simple Forecast (Holt-Winters or ARIMA placeholder)
        # using statsmodels (requires enough data points, usually > 20)
        # We just label the index.
        
        self.save_gold(daily_counts, "gold_vulnerability_index")
        return daily_counts

    # --- 2. Tech Edge Score (ML Feature Eng) ---
    def create_tech_edge_score(self):
        logger.info("Building Tech Edge Score...")
        df = self.load_silver("silver_research_papers")
        if df.empty: return

        # 1. Text Analysis (TF-IDF)
        text_data = df['title'].fillna('')
        vectorizer = TfidfVectorizer(max_features=50, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(text_data)
        
        # Feature: "Innovation Keyword Density"
        # We sum tfidf scores as a proxy for "information density"
        df['complexity_score'] = np.asarray(tfidf_matrix.sum(axis=1)).flatten()
        
        # 2. LLM Analysis (Ollama/OpenAI) for "Edge" scoring
        # If API key exists, we call it. Else we simulate.
        scores = []
        for title in df['title']:
            score = self.query_llm_for_score(title)
            scores.append(score)
        
        df['ai_innovation_score'] = scores
        
        # Normalization (0-100)
        scaler = MinMaxScaler(feature_range=(0, 100))
        df[['ai_innovation_score', 'complexity_score']] = scaler.fit_transform(df[['ai_innovation_score', 'complexity_score']])
        
        df['tech_edge_total'] = (df['ai_innovation_score'] + df['complexity_score']) / 2
        
        self.save_gold(df, "gold_tech_edge_score")
        return df

    def query_llm_for_score(self, text):
        """Mockable LLM call. Returns 0-10 score."""
        if self.openai_key:
            try:
                # Real OpenAI Call
                # response = openai.ChatCompletion.create(...)
                # return parsed_score
                return 8.5 # Validation placeholder to save tokens/cost
            except:
                return 5.0
        else:
            # Fallback / "Ollama" local logic simulation
            # Heuristic: Check for buzzwords
            buzzwords = ['agent', 'transformer', 'gpu', 'neural', 'zero-day']
            matches = sum(1 for w in buzzwords if w in text.lower())
            return min(10, matches * 2 + 5)

    # --- 3. Correlation Matrix ---
    def create_correlation_matrix(self, vuln_df, social_df):
        logger.info("Building Correlation Matrix...")
        
        if social_df is None or social_df.empty:
            social_df = self.load_silver("silver_social_signals")
        
        if social_df.empty: 
            logger.warning("No Social Data. Skipping Correlation.")
            return

        # Sentiment Analysis on Tweets
        social_df['sentiment'] = social_df['text'].apply(lambda x: TextBlob(str(x)).sentiment.polarity)
        
        # Date alignment
        # Assuming social data has ingestion timestamp or created_at
        # Use simple date simulation if missing
        dates = [self.timestamp - timedelta(days=x % 30) for x in range(len(social_df))]
        social_df['date'] = [d.date() for d in dates]
        
        daily_sentiment = social_df.groupby('date')['sentiment'].mean().reset_index(name='avg_sentiment')
        
        # Merge with Vuln Index
        if vuln_df is None or list(vuln_df.columns) == []:
             # Load if not passed
             pass # Logic simplified
        
        # We need daily risk score
        # Assuming vuln_df has 'date' and 'days_risk_score'
        
        if vuln_df is not None and not vuln_df.empty:
             daily_risk = vuln_df.groupby('date')['days_risk_score'].sum().reset_index()
             
             merged = pd.merge(daily_risk, daily_sentiment, on='date', how='inner')
             
             if not merged.empty:
                 corr_matrix = merged[['days_risk_score', 'avg_sentiment']].corr()
                 
                 # Save the matrix (melted or raw)
                 # We save the aggregated daily time series WITH the correlation features
                 self.save_gold(merged, "gold_correlation_matrix_data")
                 
                 # Save the matrix summary
                 correlation_summary = pd.DataFrame(corr_matrix).reset_index()
                 self.save_gold(correlation_summary, "gold_correlation_values")
             else:
                 logger.warning("No overlapping dates for correlation.")
        else:
             self.save_gold(daily_sentiment, "gold_social_sentiment_daily")

    def run_pipeline(self):
        vuln_index = self.create_vulnerability_index()
        self.create_tech_edge_score()
        self.create_correlation_matrix(vuln_index, None)

if __name__ == "__main__":
    refiner = GoldRefiner()
    refiner.run_pipeline()
