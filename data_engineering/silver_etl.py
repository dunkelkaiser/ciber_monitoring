import os
import glob
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path

# Try to import Great Expectations dataset
try:
    from great_expectations.dataset.pandas_dataset import PandasDataset
    from great_expectations.core.expectation_validation_result import ExpectationValidationResult
    GX_AVAILABLE = True
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
        logger.info(f"Loaded DataFrame with {len(df)} rows for '{prefix}'")
        return df

    def validate_and_save(self, df: pd.DataFrame, suite_name: str, output_name: str, expectations: list):
        """Runs GX validation and saves to Silver if allowed."""
        if df.empty:
            logger.warning(f"DataFrame for {output_name} is empty. Skipping.")
            return

        # Explicitly wrap in PandasDataset (Legacy/Core API)
        if GX_AVAILABLE:
            gx_df = PandasDataset(df)
            
            # Apply expectations
            for exp in expectations:
                method_name = exp['method']
                kwargs = exp.get('kwargs', {})
                try:
                    # Call the expectation method on the gx_df object
                    getattr(gx_df, method_name)(**kwargs)
                except AttributeError:
                    logger.warning(f"Expectation {method_name} not found on dataset object.")
                except Exception as e:
                    logger.warning(f"Error applying expectation {method_name}: {e}")

            # Validate
            validation_result = gx_df.validate()
            
            success = validation_result.success
            if not success:
                logger.warning(f"Validation failed for {output_name}. Saving anyway but logging failure.")
                logger.warning(f"Failure details: {validation_result.statistics}")
                df['data_quality_check'] = 'failed'
            else:
                df['data_quality_check'] = 'passed'
                logger.info(f"Validation Passed for {output_name}")
        else:
             df['data_quality_check'] = 'unchecked'

        # Save to Parquet
        output_path = SILVER_DIR / f"{output_name}.parquet"
        
        if output_path.exists():
            try:
                existing_df = pd.read_parquet(output_path)
                combined_df = pd.concat([existing_df, df])
            except Exception as read_err:
                 logger.error(f"Error reading existing parquet {output_path}: {read_err}. Overwriting.")
                 combined_df = df
        else:
            combined_df = df

        # Convert list/dict columns to string to ensure hashability and parquet compatibility
        for col in combined_df.columns:
            # Check safely if object type
            if combined_df[col].dtype == 'object':
                 combined_df[col] = combined_df[col].astype(str)

        combined_df = combined_df.drop_duplicates()

        # Save
        combined_df.to_parquet(output_path, index=False)
        logger.info(f"Saved {len(combined_df)} rows to {output_path}")

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
            # Map ArXiv columns: {id, title, summary, published, updated} -> {link, title, text, publication_date}
            # ArXiv ID often serves as link base, but raw usually has 'id' as url http://arxiv.org/abs/...
            if 'id' in arxiv_df.columns:
                arxiv_df.rename(columns={'id': 'link'}, inplace=True)
            if 'summary' in arxiv_df.columns:
                 arxiv_df.rename(columns={'summary': 'text'}, inplace=True)
            if 'published' in arxiv_df.columns:
                 arxiv_df.rename(columns={'published': 'publication_date'}, inplace=True)
            elif 'updated' in arxiv_df.columns:
                 arxiv_df.rename(columns={'updated': 'publication_date'}, inplace=True)

        research_df = pd.concat([nvidia_df, openai_df, arxiv_df], ignore_index=True)
        
        # Expectations for Research
        research_expectations = [
            {'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'title'}},
            {'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'link'}},
            {'method': 'expect_column_values_to_match_regex', 'kwargs': {'column': 'link', 'regex': r'^https?://'}}
        ]

        self.validate_and_save(research_df, "research_suite", "silver_research_papers", research_expectations)

        # 2. Pipeline: Vulnerabilities (CVE Mitre + Intel) (Basis for Risk Scoring)
        logger.info("--- Processing VULNERABILITY Schema ---")
        cve_df = self.load_bronze_files("cve_mitre")
        intel_df = self.load_bronze_files("intel")

        if not cve_df.empty:
            cve_df['source_entity'] = 'MITRE'
        
        if not intel_df.empty:
            intel_df['source_entity'] = 'INTEL'
        
        vuln_df = pd.concat([cve_df, intel_df], ignore_index=True)
        
        vuln_expectations = [
             {'method': 'expect_column_to_exist', 'kwargs': {'column': 'source_entity'}}
        ]
        
        if 'cve_id' in vuln_df.columns:
             vuln_expectations.append({'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'cve_id'}})

        self.validate_and_save(vuln_df, "vuln_suite", "silver_vulnerabilities", vuln_expectations)

        # 3. Pipeline: Social Signals (Twitter + Reddit)
        logger.info("--- Processing SOCIAL Schema ---")
        twitter_df = self.load_bronze_files("twitter")
        reddit_df = self.load_bronze_files("reddit")
        
        social_dfs = []

        if not twitter_df.empty:
            twitter_df['source_entity'] = 'Twitter'
            social_dfs.append(twitter_df)
        
        if not reddit_df.empty:
            reddit_df['source_entity'] = 'Reddit'
            # Map Reddit: {title, selftext, created_utc, url} -> {text, created_at, link}
            if 'selftext' in reddit_df.columns:
                # fillna('') is important for concating strings
                reddit_df['text'] = reddit_df['title'].fillna('') + " " + reddit_df['selftext'].fillna('')
            elif 'title' in reddit_df.columns:
                reddit_df['text'] = reddit_df['title']
            
            if 'created_utc' in reddit_df.columns:
                # Convert UTC timestamp to datetime
                reddit_df['created_at'] = pd.to_datetime(reddit_df['created_utc'], unit='s', errors='coerce')
            
            if 'url' in reddit_df.columns:
                 reddit_df.rename(columns={'url': 'link'}, inplace=True)

            social_dfs.append(reddit_df)

        if social_dfs:
            social_df = pd.concat(social_dfs, ignore_index=True)
        else:
            social_df = pd.DataFrame()

        if not social_df.empty:
            social_expectations = [
                 {'method': 'expect_column_values_to_not_be_null', 'kwargs': {'column': 'text'}}
            ]
            self.validate_and_save(twitter_df, "social_suite", "silver_social_signals", social_expectations)

if __name__ == "__main__":
    cleaner = SilverCleaner()
    cleaner.run_pipeline()
