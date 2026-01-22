from typing import List, Dict
import os
import json
import logging
from datetime import datetime
import praw
from dotenv import load_dotenv
from base_scraper import BaseScraper

# Load env from root directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class RedditScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="reddit")
        self.subreddits = ["cybersecurity", "intel", "amd", "nvidia", "hardware"] 
        
        # API Credentials (from .env)
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = os.getenv("REDDIT_USER_AGENT", "CyberIntelBot/1.0 by /u/dunkelkaiser")
        
    async def scrape(self) -> List[Dict]:
        results = []
        
        # Check for Standby Mode
        if not self.client_id or not self.client_secret:
            self.logger.warning("Reddit Scraper is in STANDBY MODE (Pending API Credentials).")
            self.logger.info("Skipping Reddit scrape to avoid errors. Update .env once approved.")
            return []

        try:
            self.logger.info("Initializing PRAW Client...")
            reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            
            for sub_name in self.subreddits:
                self.logger.info(f"Scraping r/{sub_name} via API...")
                subreddit = reddit.subreddit(sub_name)
                
                # Fetch top New posts
                for post in subreddit.new(limit=10):
                    res = {
                        "title": post.title,
                        "content": post.selftext, 
                        "subreddit": sub_name,
                        "url": f"https://www.reddit.com{post.permalink}",
                        "created_at": datetime.utcfromtimestamp(post.created_utc).isoformat(), 
                        "scraped_date": datetime.utcnow().isoformat(),
                        "source_entity": "Reddit"
                    }
                    results.append(res)
                    
        except Exception as e:
            self.logger.error(f"Reddit API Error: {e}")

        self.logger.info(f"Scrape collected {len(results)} items via PRAW.")
        return results

if __name__ == "__main__":
    # Test Run
    import asyncio
    scraper = RedditScraper()
    data = asyncio.run(scraper.scrape())
    print(json.dumps(data, indent=2))
