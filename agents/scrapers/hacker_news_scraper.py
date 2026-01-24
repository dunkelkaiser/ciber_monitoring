import requests
import json
import logging
import os
import asyncio
from typing import List, Dict
from datetime import datetime
from base_scraper import BaseScraper
from dotenv import load_dotenv

# Load env from root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class HackerNewsScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="hacker_news")
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.keywords = ["cybersecurity", "security", "vulnerability", "exploit", "hack", "intel", "nvidia", "hardware", "ai", "leak"]

    async def get_item(self, item_id: int) -> Dict:
        """Fetches details of a single item from HN API."""
        url = f"{self.base_url}/item/{item_id}.json"
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching HN item {item_id}: {e}")
        return {}

    async def scrape(self) -> List[Dict]:
        """Scrapes HN Top Stories and filters for relevant tech/security items."""
        self.logger.info("Fetching Hacker News Top Stories IDs...")
        top_stories_url = f"{self.base_url}/topstories.json"
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, requests.get, top_stories_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch top stories: {response.status_code}")
                return []
            
            story_ids = response.json()[:100] # Limit to top 100 for efficiency
            self.logger.info(f"Retrieved {len(story_ids)} top story IDs. Fetching details...")
            
            tasks = [self.get_item(sid) for sid in story_ids]
            items = await asyncio.gather(*tasks)
            
            results = []
            for item in items:
                if not item: continue
                
                title = item.get("title", "").lower()
                text = item.get("text", "").lower()
                
                # Check if item is relevant to our keywords
                is_relevant = any(kw in title or kw in text for kw in self.keywords)
                
                if is_relevant:
                    # Map to standardization fields
                    # time in HN is unix timestamp
                    created_at = datetime.utcfromtimestamp(item.get("time", 0)).isoformat()
                    
                    res = {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "text": item.get("text") or "", # HN stories usually have text OR url
                        "url": item.get("url"),
                        "score": item.get("score", 0),
                        "descendants": item.get("descendants", 0), # Total comments
                        "created_at": created_at,
                        "scraped_date": datetime.utcnow().isoformat(),
                        "source_entity": "HackerNews",
                        "platform": "HackerNews"
                    }
                    results.append(res)
            
            self.logger.info(f"Filtered {len(results)} relevant items from Hacker News.")
            return results

        except Exception as e:
            self.logger.error(f"Critical error in HN Scraper: {e}")
            return []

if __name__ == "__main__":
    # Test Run
    import asyncio
    scraper = HackerNewsScraper()
    data = asyncio.run(scraper.scrape())
    print(json.dumps(data, indent=2))
