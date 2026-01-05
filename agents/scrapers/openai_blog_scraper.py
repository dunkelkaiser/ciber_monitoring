from typing import List, Dict
import asyncio
from base_scraper import BaseScraper

class OpenAIBlogScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="openai")
        self.base_url = self.scraper_config.get("base_url")

    async def scrape(self) -> List[Dict]:
        if not self.use_playwright:
             raise RuntimeError("OpenAI scraper requires Playwright")

        results = []
        page = await self.context.new_page()
        
        try:
            self.logger.info(f"Navigating to {self.base_url}")
            await page.goto(self.base_url, wait_until="networkidle")
            
            # OpenAI blog uses infinite scroll or Load More buttons often
            # Basic implementation for grid items
            
            # Wait for grid
            await page.wait_for_selector("div.ui-grid-cols-3", timeout=10000)
            
            articles = await page.locator("div.ui-grid-cols-3 > div").all()
            
            for article in articles[:10]: # Limit to first 10 for safety
                try:
                    title_el = article.locator("h3")
                    date_el = article.locator("div.text-xs") # approximate selector
                    link_el = article.locator("a").first
                    
                    if await title_el.count() > 0:
                        title = await title_el.inner_text()
                        link = await link_el.get_attribute("href")
                        
                        if link and not link.startswith("http"):
                            link = f"https://openai.com{link}"
                            
                        results.append({
                            "title": title,
                            "url": link,
                            "source": "openai_blog",
                            # Date extraction might be tricky dynamically
                        })
                except Exception as inner_e:
                    # Individual article failure shouldn't stop the whole scrape
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error scraping OpenAI: {e}")
        finally:
            await page.close()
            
        return results
