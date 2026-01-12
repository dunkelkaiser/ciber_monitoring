from typing import List, Dict
import tweepy
import os
import re
from base_scraper import BaseScraper
from datetime import datetime, timezone

class TwitterScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="twitter")
        self.output_dir = self.scraper_config.get("output_dir", "data/bronze")
        self.queries = self.scraper_config.get("queries", [])
        self.max_results = self.scraper_config.get("max_results", 5)
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self.client = None

    async def scrape(self) -> List[Dict]:
        if not self.bearer_token:
            self.logger.warning("No Twitter Bearer Token found. Skipping.")
            return []

        if not self.client:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
        
        results = []
        scraped_date = datetime.now(timezone.utc).isoformat()

        for query in self.queries:
            self.logger.info(f"Searching Twitter for: {query}")
            try:
                # Add rate limiting wait manually if needed, though tweepy handles some
                await self._rate_limit_wait()
                
                tweets = self.client.search_recent_tweets(
                    query=query,
                    max_results=self.max_results,
                    tweet_fields=['created_at', 'public_metrics', 'author_id']
                )

                if not tweets.data:
                    continue

                for tweet in tweets.data:
                    # Parse created_at to ISO string if it isn't already (tweepy usually returns datetime object)
                    published_date = tweet.created_at.isoformat() if tweet.created_at else None

                    results.append({
                        "tweet_id": str(tweet.id),
                        "text": tweet.text,
                        "created_at": published_date, # keeping legacy field
                        "published_date": published_date, # New standard field
                        "scraped_date": scraped_date,
                        "metrics": tweet.public_metrics,
                        "query_matched": query,
                        "mentioned_cves": self._extract_cves(tweet.text),
                        "source": "twitter"
                    })
                    
            except Exception as e:
                self.logger.error(f"Twitter search failed for {query}: {e}")
                
        return results

    def _extract_cves(self, text: str) -> List[str]:
        return re.findall(r'CVE-\d{4}-\d{4,7}', text, re.IGNORECASE)
