from typing import List, Dict
import praw
from datetime import datetime
import os
from base_scraper import BaseScraper

class RedditScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="reddit")
        self.client_id = self.scraper_config.get("client_id") or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = self.scraper_config.get("client_secret") or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = self.scraper_config.get("user_agent", "python:ciber_monitoring:v1.0")
        self.subreddits = self.scraper_config.get("subreddits", ["cybersecurity"])
        self.limit = self.scraper_config.get("limit", 100)
        self.reddit = None

    async def scrape(self) -> List[Dict]:
        if not self.client_id or not self.client_secret:
            self.logger.warning("Reddit credentials not found. Skipping.")
            return []

        if not self.reddit:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            # PRAW is blocking, but for simple queries it might be okay or we can wrap in thread
            # however, BaseScraper is async. 
            # Ideally we should use asyncpraw, but requirements.txt specified praw.
            # We will use it synchronously in this async function for now as it's just IO mostly.

        results = []
        scraped_date = datetime.utcnow().isoformat() + "Z"

        for sub_name in self.subreddits:
            self.logger.info(f"Scraping subreddit: {sub_name}")
            try:
                subreddit = self.reddit.subreddit(sub_name)
                # Use .new() or .hot()
                for post in subreddit.new(limit=self.limit):
                    
                    # Handle date
                    published_ts = post.created_utc
                    published_date = datetime.utcfromtimestamp(published_ts).isoformat() + "Z"

                    post_data = {
                        "title": post.title,
                        "content": post.selftext,
                        "author": str(post.author),
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "url": post.url,
                        "permalink": f"https://reddit.com{post.permalink}",
                        "subreddit": sub_name,
                        "published_date": published_date,
                        "scraped_date": scraped_date,
                        "source": "reddit"
                    }
                    results.append(post_data)

            except Exception as e:
                self.logger.error(f"Error scraping subreddit {sub_name}: {e}")

        self.logger.info(f"Collected {len(results)} posts from Reddit.")
        return results
