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
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

# Optional API imports
try:
    import openai
    from anthropic import Anthropic
    import google.generativeai as genai
    from dotenv import load_dotenv
except ImportError:
    pass

import uuid

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("GoldETL")

# Paths
BASE_DIR = Path(__file__).resolve().parent
SILVER_DIR = BASE_DIR / "silver"
GOLD_DIR = BASE_DIR / "gold"
ENV_PATH = BASE_DIR.parent / ".env"

# Load Env
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    logger.info(f"Loaded environment variables from {ENV_PATH}")
else:
    logger.warning(f".env file not found at {ENV_PATH}")

GOLD_DIR.mkdir(parents=True, exist_ok=True)

class GoldRefiner:
    def __init__(self):
        self.timestamp = datetime.now()
        self.run_id = str(uuid.uuid4())
        self.run_ts = self.timestamp
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

    def save_gold(self, df: pd.DataFrame, name: str, subset: list = None):
        if df.empty:
            logger.warning(f"DataFrame for {name} is empty. Skipping gold save.")
            return

        # Add Run Metadata
        df['run_id'] = self.run_id
        df['run_ts'] = self.run_ts
        
        output_path = GOLD_DIR / f"{name}.parquet"
        
        # Load existing if available
        if output_path.exists():
            try:
                existing_df = pd.read_parquet(output_path)
                df = pd.concat([existing_df, df], ignore_index=True)
            except Exception as e:
                logger.error(f"Failed to load existing gold file {name}: {e}")
                # Use current df as base if read fails (or handle differently based on policy)

        # Deduplicate
        if subset:
            # If specific keys provided
            df.drop_duplicates(subset=subset, keep='last', inplace=True)
        else:
             # Default: Drop identical rows including run metadata? 
             # No, if we want history, we should probably only drop if content is identical BUT different run_id?
             # User said: "concatenar + drop_duplicates por clave"
             # If no key provided, let's just drop exact duplicates across all columns to be safe
             df.drop_duplicates(inplace=True)

        # Convert objects to string for Parquet safety
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str)
                
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved Gold Dataset: {name} (Total rows: {len(df)}) [Run ID: {self.run_id}]")
        
        # Simulating SQL Export
        sql_name = name.replace("gold_", "")
        logger.info(f"[SQL Bridge] Data ready for loading into PostgreSQL table '{sql_name}'.")

    # --- 1. Vulnerability Index (Time Series) ---
    def create_vulnerability_index(self):
        logger.info("Building Vulnerability Index...")
        df = self.load_silver("silver_vulnerabilities")
        if df.empty: return

        # Normalize Date Semantics
        # 1. event_date (When it happened/published)
        if 'published_date' not in df.columns or df['published_date'].iloc[0] == "UNKNOWN":
            logger.info("Simulating historical dates for Time Series Analysis...")
            # Distribute items over last 30 days
            dates = [self.timestamp - timedelta(days=x % 30) for x in range(len(df))]
            df['event_date'] = pd.to_datetime(dates).floor('D')
        else:
             df['event_date'] = pd.to_datetime(df['published_date'], errors='coerce').fillna(self.timestamp).dt.floor('D')
        
        # 2. asof_date (Processing date/Batch date)
        df['asof_date'] = pd.to_datetime(self.timestamp).floor('D')
        
        # Aggregation: Count per asof_date, event_date, source
        # We group by these to keep granular history.
        group_cols = ['asof_date', 'event_date', 'source_entity']
        daily_counts = df.groupby(group_cols).size().reset_index(name='count')
        
        # Risk Severity Weighting (Simulation logic if severity is missing)
        # If we had 'severity' col "HIGH", "CRITICAL"...
        daily_counts['days_risk_score'] = daily_counts['count'] * 10 # Base score
        
        # Advanced: Rolling Average (Time Series Feature - per entity sorted by event_date)
        daily_counts = daily_counts.sort_values('event_date')
        daily_counts['risk_moving_avg_7d'] = daily_counts.groupby('source_entity')['days_risk_score'].transform(lambda x: x.rolling(7, min_periods=1).mean())
        
        # Save gold (append mode handles history)
        # We need to decide what to dedup on. 'asof_date' makes it unique for this run effectively? 
        # Actually, if we run multiple times a day, `asof_date` (floored) is same. `run_id` handles that uniqueness in storage.
        # But logically, if we just want "daily snapshot", maybe we dedup on asof_date+event_date+source?
        # User said "Gold no debe sobrescribirse... mantener histórico".
        # So we append.
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
        
        # 2. Parallel LLM Analysis for "Edge" scoring
        logger.info(f"Processing {len(df)} titles with LLM in parallel...")
        
        # Limit workers to avoid hitting rate limits too fast (adjust as needed)
        max_workers = 10 
        scores = [5.0] * len(df) # Default values
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Create a mapping of future to index
            future_to_idx = {executor.submit(self.query_llm_for_score, title): i for i, title in enumerate(df['title'])}
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    scores[idx] = future.result()
                except Exception as e:
                    logger.error(f"Future for index {idx} failed: {e}")
                    scores[idx] = 5.0
        
        df['ai_innovation_score'] = scores
        
        # Normalization (0-100)
        scaler = MinMaxScaler(feature_range=(0, 100))
        df[['ai_innovation_score', 'complexity_score']] = scaler.fit_transform(df[['ai_innovation_score', 'complexity_score']])
        
        df['tech_edge_total'] = (df['ai_innovation_score'] + df['complexity_score']) / 2

        # Date Fallback Strategy (Ticket 1)
        # Priority: run_ts > scraped_date > published_date > self.timestamp
        # First, ensure all potential date columns are datetime objects, coercing errors
        potential_dates = ['run_ts', 'scraped_date', 'published_date']
        for col in potential_dates:
             if col in df.columns:
                 df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
        
        # Initialize final_date with self.timestamp (lowest priority)
        final_date = pd.Series([self.timestamp.replace(tzinfo=None)] * len(df), index=df.index)
        
        # Apply cascade in reverse order of priority to overwrite
        if 'published_date' in df.columns:
            final_date = df['published_date'].combine_first(final_date)
        if 'scraped_date' in df.columns:
            final_date = df['scraped_date'].combine_first(final_date)
        if 'run_ts' in df.columns:
             final_date = df['run_ts'].combine_first(final_date)
            
        df['run_ts'] = final_date.dt.strftime("%Y-%m-%d")

        self.save_gold(df, "gold_tech_edge_score")
        return df

    def query_llm_for_score(self, text):
        """Mockable LLM call. Returns 0-10 score."""
        if self.openai_key:
            try:
                # Real OpenAI Call
                client = openai.OpenAI(api_key=self.openai_key)
                response = client.chat.completions.create(
                    model="gpt-5-nano-2025-08-07",
                    messages=[
                        {"role": "system", "content": "You are a tech analyst. Rate the 'innovation level' of the following research title from 0 to 10. Return ONLY the number."},
                        {"role": "user", "content": text}
                    ],
                    max_completion_tokens=50
                )
                score_raw = response.choices[0].message.content.strip()
                # Robust parsing: extract the first number found in the string
                match = re.search(r"(\d+\.?\d*)", score_raw)
                if match:
                    return float(match.group(1))
                else:
                    logger.warning(f"No numeric value found in LLM response: '{score_raw}'. Falling back to 5.0")
                    return 5.0
            except Exception as e:
                logger.warning(f"OpenAI Call failed for '{text[:50]}...': {e}. Using fallback 5.0")
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

        # Sentiment Analysis on Tweets/Reddit
        if 'sentiment' not in social_df.columns:
            # Use unified 'text' column if available (Ticket 3)
             if 'text' in social_df.columns:
                 social_df['sentiment'] = social_df['text'].apply(lambda x: TextBlob(str(x)).sentiment.polarity)
             else:
                 logger.warning("No 'text' column for sentiment analysis.")
                 social_df['sentiment'] = 0.0

        # Date Alignment (Ticket 4)
        # Use 'published_date' (Standardized in Ticket 2)
        if 'published_date' in social_df.columns:
             # Ensure datetime
             social_df['event_date'] = pd.to_datetime(social_df['published_date'], errors='coerce').dt.floor('D')
        else:
             # Fallback to current run date (asof_date) if published_date missing
             logger.warning("No 'published_date' in social data, using asof_date for event_date.")
             social_df['event_date'] = pd.to_datetime(self.timestamp).floor('D')
             
        # Aggregate Social: Daily Average Sentiment and Volume per Platform (Ticket 5)
        # We group by event_date AND platform
        platform_metrics = social_df.groupby(['event_date', 'platform']).agg({
            'sentiment': 'mean',
            'text': 'count'
        }).reset_index()
        platform_metrics.rename(columns={'sentiment': 'avg_sentiment', 'text': 'volume'}, inplace=True)
        
        # Add asof_date for tracking
        platform_metrics['asof_date'] = pd.to_datetime(self.timestamp).floor('D')
        
        # Save historical social metrics
        self.save_gold(platform_metrics, "gold_social_metrics_daily", subset=['event_date', 'platform'])
        
        # Aggregate Social: Daily Global Average Sentiment for Correlation
        daily_sentiment = social_df.groupby('event_date')['sentiment'].mean().reset_index(name='avg_sentiment')
        
        # Aggregate Risk: Daily Total Risk
        if vuln_df is None or vuln_df.empty:
             logger.warning("No Risk Data (vuln_df) provided for correlation.")
             daily_risk = pd.DataFrame(columns=['event_date', 'days_risk_score_total'])
        else:
             if 'event_date' in vuln_df.columns and 'days_risk_score' in vuln_df.columns:
                  daily_risk = vuln_df.groupby('event_date')['days_risk_score'].sum().reset_index(name='days_risk_score_total')
             else:
                  logger.warning("vuln_df missing expected columns.")
                  daily_risk = pd.DataFrame(columns=['event_date', 'days_risk_score_total'])

        # FIX: Ensure both are Timezone Naive before merge
        if not daily_risk.empty and 'event_date' in daily_risk.columns:
             if hasattr(daily_risk['event_date'].dt, 'tz_localize'):
                  daily_risk['event_date'] = daily_risk['event_date'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)

        if not daily_sentiment.empty and 'event_date' in daily_sentiment.columns:
             if hasattr(daily_sentiment['event_date'].dt, 'tz_localize'):
                  daily_sentiment['event_date'] = daily_sentiment['event_date'].apply(lambda x: x.replace(tzinfo=None) if pd.notnull(x) else x)

        merged = pd.merge(daily_risk, daily_sentiment, on='event_date', how='outer')
        
        merged['days_risk_score_total'] = merged['days_risk_score_total'].fillna(0)
        merged['avg_sentiment'] = merged['avg_sentiment'].fillna(0)
        merged['asof_date'] = pd.to_datetime(self.timestamp).floor('D')
        
        if not merged.empty:
             # Calculate correlation between global sentiment and risk
             corr_matrix = merged[['days_risk_score_total', 'avg_sentiment']].corr()
             self.save_gold(merged, "gold_fact_risk_sentiment_daily", subset=['event_date'])
             
             correlation_summary = pd.DataFrame(corr_matrix).reset_index()
             self.save_gold(correlation_summary, "gold_correlation_values")
        else:
             logger.warning("Merged dataframe empty. Skipping save.")

    def run_pipeline(self):
        vuln_index = self.create_vulnerability_index()
        self.create_tech_edge_score()
        self.create_correlation_matrix(vuln_index, None)

if __name__ == "__main__":
    refiner = GoldRefiner()
    refiner.run_pipeline()
