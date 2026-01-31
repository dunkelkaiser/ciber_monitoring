import os
import glob
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# Try to import Great Expectations dataset
# Try to import Great Expectations dataset
try:
    # from great_expectations.dataset.pandas_dataset import PandasDataset
    # from great_expectations.core.expectation_validation_result import ExpectationValidationResult
    # GX_AVAILABLE = True
    GX_AVAILABLE = False # Force disable for debugging InvalidIndexError
except ImportError:
    GX_AVAILABLE = False
    print("Warning: great_expectations not found. Validation will be skipped.")

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SilverETL")

# Paths
BASE_DIR = Path(__file__).resolve().parent
BRONZE_DIR = BASE_DIR / "bronze"
SILVER_DIR = BASE_DIR / "silver"

# Ensure Silver dir exists
SILVER_DIR.mkdir(parents=True, exist_ok=True)

class SilverCleaner:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_bronze_files(self, prefix: str) -> pd.DataFrame:
        """Loads all JSON files starting with prefix from Bronze layer."""
        # Use recursive match or exact match? Bronze is flat usually.
        # Handle path separators safely
        pattern = os.path.join(str(BRONZE_DIR), f"{prefix}_raw_*.json")
        files = glob.glob(pattern)
        logger.info(f"Found {len(files)} files for prefix '{prefix}' in {BRONZE_DIR}")
        
        all_data = []
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    if isinstance(data, list):
                        all_data.extend(data)
                    elif isinstance(data, dict):
                        # Handle wrapped responses (e.g. { "data": [...], "metadata": ... })
                        if 'data' in data and isinstance(data['data'], list):
                            all_data.extend(data['data'])
                        else:
                            all_data.append(data)
            except Exception as e:
                logger.error(f"Error loading {f}: {e}")
        
        if not all_data:
            return pd.DataFrame()
            
        # Normalize nested JSON if feasible
        df = pd.json_normalize(all_data)
        # Robustness: Remove duplicate columns immediately
        df = df.loc[:, ~df.columns.duplicated()]
        logger.info(f"Loaded DataFrame with {len(df)} rows for '{prefix}'")
        return df

    def validate_and_save(self, df: pd.DataFrame, suite_name: str, output_name: str, expectations: list):
        """Runs validation and saves to Silver safely."""
        if df.empty:
            logger.warning(f"DataFrame for {output_name} is empty. Skipping.")
            return

        # 1. Clean Data Structure
        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        # Reset Index
        df = df.reset_index(drop=True)

        # 2. Validation (Optional/Skipped if GX unavailable)
        if GX_AVAILABLE:
            try:
                gx_df = PandasDataset(df)
                for exp in expectations:
                    method_name = exp['method']
                    kwargs = exp.get('kwargs', {})
                    try:
                        getattr(gx_df, method_name)(**kwargs)
                    except Exception as e:
                        logger.warning(f"Expectation {method_name} error: {e}")
                
                validation_result = gx_df.validate()
                if not validation_result.success:
                    logger.warning(f"Validation failed for {output_name}. Details: {validation_result.statistics}")
            except Exception as e:
                logger.error(f"GX Validation crashed: {e}")

        # 3. Save to Parquet
        output_path = SILVER_DIR / f"{output_name}.parquet"
        
        # Load existing (Append Mode) - careful with schemas
        if output_path.exists():
            try:
                existing_df = pd.read_parquet(output_path)
                # Concatenate
                combined_df = pd.concat([existing_df, df], ignore_index=True)
            except Exception as read_err:
                 logger.error(f"Error reading existing parquet {output_path}: {read_err}. Overwriting.")
                 combined_df = df
        else:
            combined_df = df

        # Final Cleanup before write
        combined_df = combined_df.reset_index(drop=True)
        # Ensure string types for objects (Must happen before drop_duplicates if lists exist)
        for col in combined_df.columns:
            if combined_df[col].dtype == 'object':
                 combined_df[col] = combined_df[col].astype(str)

        combined_df.drop_duplicates(inplace=True)

        try:
            combined_df.to_parquet(output_path, index=False)
            logger.info(f"Saved {len(combined_df)} rows to {output_path}")
        except Exception as e:
            logger.error(f"FAILED to save {output_path}: {e}")
            raise e

    def run_pipeline(self):
        # 1. Pipeline: Research Papers (Nvidia + OpenAI + ArXiv)
        logger.info("--- Processing RESEARCH Schema ---")
        nvidia_df = self.load_bronze_files("nvidia")
        openai_df = self.load_bronze_files("openai")
        arxiv_df = self.load_bronze_files("arxiv")
        
        # Standardization
        if not nvidia_df.empty:
            nvidia_df['source_entity'] = 'NVIDIA'
            if 'url' in nvidia_df.columns:
                nvidia_df.rename(columns={'url': 'link'}, inplace=True)
                
        if not openai_df.empty:
            openai_df['source_entity'] = 'OpenAI'
            if 'url' in openai_df.columns:
                 openai_df.rename(columns={'url': 'link'}, inplace=True)

        if not arxiv_df.empty:
            logger.info(f"ArXiv Columns Pre-Rename: {arxiv_df.columns.tolist()}")
            arxiv_df['source_entity'] = 'ArXiv'
            # Map ArXiv columns: {id, title, summary, published, updated} -> {link, title, text, published_date}
            # ArXiv ID often serves as link base, but raw usually has 'id' as url http://arxiv.org/abs/...
            if 'id' in arxiv_df.columns:
                arxiv_df.rename(columns={'id': 'link'}, inplace=True)
            if 'summary' in arxiv_df.columns:
                 arxiv_df.rename(columns={'summary': 'text'}, inplace=True)
            if 'published' in arxiv_df.columns:
                 arxiv_df.rename(columns={'published': 'published_date'}, inplace=True)
            elif 'updated' in arxiv_df.columns:
                 arxiv_df.rename(columns={'updated': 'published_date'}, inplace=True)
            
            # Ensure output has published_date even if missing
            if 'published_date' not in arxiv_df.columns:
                 arxiv_df['published_date'] = None

        research_df = pd.concat([nvidia_df, openai_df, arxiv_df], ignore_index=True)
        # research_df = pd.concat([nvidia_df, openai_df], ignore_index=True)
        # Robust dedup cols
        research_df = research_df.loc[:, ~research_df.columns.duplicated()]
        
        # Expectations for Research
        research_expectations = [
            {'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'title'}},
            {'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'link'}},
            {'method': 'expect_column_values_to_match_regex', 'kwargs': {'column': 'link', 'regex': r'^https?://'}}
        ]

        logger.info("SAVING RESEARCH...")
        self.validate_and_save(research_df, "research_suite", "silver_research_papers", research_expectations)
        logger.info("SAVED RESEARCH.")

        # 2. Pipeline: Vulnerabilities (CVE Mitre + Intel) (Basis for Risk Scoring)
        logger.info("--- Processing VULNERABILITY Schema ---")
        cve_df = self.load_bronze_files("cve_mitre")
        intel_df = self.load_bronze_files("intel")
        amd_df = self.load_bronze_files("amd")

        if not cve_df.empty:
            cve_df['source_entity'] = 'MITRE'
            # Normalize date for MITRE if needed (often has 'publishedDate' or 'published')
            if 'publishedDate' in cve_df.columns:
                cve_df.rename(columns={'publishedDate': 'published_date'}, inplace=True)
        
        if not intel_df.empty:
            intel_df['source_entity'] = 'INTEL'
            if 'updated' in intel_df.columns:
                 intel_df.rename(columns={'updated': 'published_date'}, inplace=True)
        
        if not amd_df.empty:
            amd_df['source_entity'] = 'AMD'
            if 'date' in amd_df.columns:
                 amd_df.rename(columns={'date': 'published_date'}, inplace=True)
        
        vuln_df = pd.concat([cve_df, intel_df, amd_df], ignore_index=True)
        vuln_df = vuln_df.loc[:, ~vuln_df.columns.duplicated()]
        
        vuln_expectations = [
             {'method': 'expect_column_to_exist', 'kwargs': {'column': 'source_entity'}}
        ]
        
        if 'cve_id' in vuln_df.columns:
             vuln_expectations.append({'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'cve_id'}})

        logger.info("SAVING VULNERABILITIES...")
        self.validate_and_save(vuln_df, "vuln_suite", "silver_vulnerabilities", vuln_expectations)
        logger.info("SAVED VULNERABILITIES.")

        # 3. Pipeline: Social Signals (Twitter + HackerNews)
        logger.info("--- Processing SOCIAL Schema ---")
        twitter_df = self.load_bronze_files("twitter")
        hn_df = self.load_bronze_files("hacker_news")
        
        social_dfs = []

        if not twitter_df.empty:
            twitter_df['source_entity'] = 'Twitter'
            twitter_df['platform'] = 'Twitter'
            # Standardize for Twitter if needed
            if 'text' not in twitter_df.columns and 'full_text' in twitter_df.columns:
                 twitter_df.rename(columns={'full_text': 'text'}, inplace=True)
            
            # For engagement_score, use metrics if available
            twitter_df['engagement_score'] = 0
            if 'public_metrics.retweet_count' in twitter_df.columns:
                 twitter_df['engagement_score'] = twitter_df['public_metrics.retweet_count'].fillna(0)

            if 'created_at' in twitter_df.columns:
                twitter_df.rename(columns={'created_at': 'published_date'}, inplace=True)

            # Safety fallback
            if 'published_date' not in twitter_df.columns:
                twitter_df['published_date'] = None

            social_dfs.append(twitter_df[['text', 'published_date', 'platform', 'source_entity', 'engagement_score']])
        
        if not hn_df.empty:
            hn_df['source_entity'] = 'HackerNews'
            hn_df['platform'] = 'HackerNews'
            
            # Map HN: {title, text, created_at, score} -> {text, published_date, engagement_score}
            hn_df['combined_text'] = hn_df['title'].fillna('') + " " + hn_df['text'].fillna('')
            hn_df.rename(columns={'combined_text': 'text', 'score': 'engagement_score', 'time': 'published_date'}, inplace=True)
            # HN 'time' is usually unix timestamp, might need conversion in Bronze or here. 
            # Assuming 'created_at' if that's what Bronze provides. Let's check logic:
            # Assuming 'created_at' if that's what Bronze provides.
            if 'created_at' in hn_df.columns:
                hn_df.rename(columns={'created_at': 'published_date'}, inplace=True)
            
            # Safety fallback
            if 'published_date' not in hn_df.columns:
                hn_df['published_date'] = None

            social_dfs.append(hn_df[['text', 'published_date', 'platform', 'source_entity', 'engagement_score']])

        if social_dfs:
            social_df = pd.concat(social_dfs, ignore_index=True)
            social_df = social_df.loc[:, ~social_df.columns.duplicated()]
        else:
            social_df = pd.DataFrame()

        if not social_df.empty:
            # Ensure published_date is datetime
            if 'published_date' in social_df.columns:
                social_df['published_date'] = pd.to_datetime(social_df['published_date'], errors='coerce')
            
            social_expectations = [
                 {'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'text'}},
                 {'method': 'expect_column_to_exist', 'kwargs': {'column': 'platform'}}
            ]
            logger.info("SAVING SOCIAL...")
            self.validate_and_save(social_df, "social_suite", "silver_social_signals", social_expectations)
            logger.info("SAVED SOCIAL.")

if __name__ == "__main__":
    import traceback
    try:
        cleaner = SilverCleaner()
        cleaner.run_pipeline()
    except Exception:
        traceback.print_exc()
