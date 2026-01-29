import asyncio
import logging
import sys
from arxiv_scraper import ArxivScraper
from hacker_news_scraper import HackerNewsScraper
from amd_scraper import AMDScraper

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

async def test_hn_structure():
    logger.info("Testing HackerNewsScraper...")
    try:
        scraper = HackerNewsScraper()
        # HN uses public API, so we can actually test a small scrape
        results = await scraper.scrape()
        
        if not results:
            logger.warning("⚠️ HackerNews returned no results (might be no current relevant news).")
            # We count it as pass if NO ERROR occurs
            return True
            
        logger.info(f"✅ HackerNewsScraper passed. Got {len(results)} items.")
        return True
    except Exception as e:
        logger.error(f"❌ HackerNewsScraper failed: {e}")
        return False

async def test_amd():
    logger.info("Testing AMDScraper...")
    try:
        scraper = AMDScraper()
        # Test the robust scrape
        results = await scraper.scrape()
        
        if not results:
            logger.error("❌ AMDScraper returned no results.")
            return False
            
        first = results[0]
        required_fields = ["advisory_id", "title", "source_url", "vendor"]
        for field in required_fields:
            if field not in first:
                logger.error(f"❌ Missing field '{field}' in AMD record.")
                return False
                
        logger.info(f"✅ AMDScraper passed. Got {len(results)} items. Sample: {first['advisory_id']} - {first['title']}")
        return True
    except Exception as e:
        logger.error(f"❌ AMDScraper failed: {e}")
        return False

async def main():
    pass_arxiv = await test_arxiv()
    pass_hn = await test_hn_structure()
    pass_amd = await test_amd()
    
    if pass_arxiv and pass_hn and pass_amd:
        logger.info("🎉 All verification tests passed!")
        sys.exit(0)
    else:
        logger.error("⚠️ Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
