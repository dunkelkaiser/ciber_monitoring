import asyncio
import argparse
import logging
import sys
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Import scrapers
from cve_mitre_scraper import CVEMitreScraper
from nvidia_scraper import NVIDIAScraper
from intel_scraper import IntelScraper
from twitter_scraper import TwitterScraper
from openai_blog_scraper import OpenAIScraper
from reddit_scraper import RedditScraper
from arxiv_scraper import ArxivScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("Orchestrator")

async def run_scraper(scraper, semaphore=None):
    """Wrapper to run a single scraper with error handling."""
    if semaphore:
        async with semaphore:
            await scraper.run()
    else:
        await scraper.run()

async def main():
    parser = argparse.ArgumentParser(description="Web Scraper Orchestrator")
    parser.add_argument("--initial-load", action="store_true", help="Run all scrapers")
    parser.add_argument("--scraper", type=str, help="Run a specific scraper by name")
    parser.add_argument("--parallel", action="store_true", help="Run scrapers in parallel")
    
    args = parser.parse_args()
    
    # Registry of available scrapers
    scrapers_map = {
        "cve_mitre": CVEMitreScraper,
        "nvidia": NVIDIAScraper,
        "intel": IntelScraper,
        "twitter": TwitterScraper,
        "openai": OpenAIScraper,
        "reddit": RedditScraper,
        "arxiv": ArxivScraper
    }
    
    to_run = []
    
    if args.scraper:
        if args.scraper.lower() == 'all':
             to_run = [cls() for cls in scrapers_map.values()]
        elif args.scraper in scrapers_map:
            to_run.append(scrapers_map[args.scraper]())
        else:
            logger.error(f"Scraper '{args.scraper}' not found. Available: {list(scrapers_map.keys())}")
            sys.exit(1)
    elif args.initial_load:
        to_run = [cls() for cls in scrapers_map.values()]
    else:
        logger.warning("No action specified. Use --initial-load or --scraper=<name>")
        sys.exit(0)

    logger.info(f"Starting execution of {len(to_run)} scrapers...")
    
    if args.parallel:
        # Limit concurrency to avoid resource exhaustion
        semaphore = asyncio.Semaphore(3)
        tasks = [run_scraper(s, semaphore) for s in to_run]
        await asyncio.gather(*tasks)
    else:
        for scraper in to_run:
            await run_scraper(scraper)

    logger.info("Orchestration complete.")

if __name__ == "__main__":
    asyncio.run(main())
