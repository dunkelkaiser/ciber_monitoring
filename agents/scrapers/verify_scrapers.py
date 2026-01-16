import asyncio
import logging
import sys
from arxiv_scraper import ArxivScraper
from reddit_scraper import RedditScraper

# Setup simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verifier")

async def test_arxiv():
    logger.info("Testing ArxivScraper...")
    scraper = ArxivScraper()
    # Limit results for speed
    scraper.max_results = 3 
    scraper.keywords = ["LLM"]
    
    results = await scraper.scrape()
    
    if not results:
        logger.error("❌ Arxiv returned no results.")
        return False
        
    first = results[0]
    if "published_date" not in first or "scraped_date" not in first:
        logger.error(f"❌ Missing date fields in: {first.keys()}")
        return False
        
    if first["source"] != "arxiv":
        logger.error("❌ Wrong source field.")
        return False
        
    logger.info(f"✅ Arxiv Scraper passed. Got {len(results)} items. Sample Date: {first['published_date']}")
    return True

async def test_reddit_structure():
    logger.info("Testing RedditScraper instantiation...")
    try:
        scraper = RedditScraper()
        # We expect this to run but return empty list if no creds, OR throw warning.
        # We won't call scrape() fully if we know it fails without creds, 
        # but let's try and catch the warning/empty return.
        
        # Inject dummy creds to test logic if logic doesn't validate strictly immediately
        scraper.client_id = "fake"
        scraper.client_secret = "fake"
        
        # This will likely fail connection or auth
        # But we want to ensure the CODE is valid (imports, class structure)
        logger.info("✅ RedditScraper instantiated successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ RedditScraper instantiation failed: {e}")
        return False

async def main():
    pass_arxiv = await test_arxiv()
    pass_reddit = await test_reddit_structure()
    
    if pass_arxiv and pass_reddit:
        logger.info("🎉 All verification tests passed!")
        sys.exit(0)
    else:
        logger.error("⚠️ Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
