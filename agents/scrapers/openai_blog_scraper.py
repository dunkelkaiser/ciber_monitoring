from typing import List, Dict
from base_scraper import BaseScraper
import asyncio
from datetime import datetime, timezone

class OpenAIScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="openai")
        self.base_url = self.scraper_config.get("base_url", "https://openai.com/research")
        self.timeout = self.scraper_config.get("timeout", 60000)

    async def scrape(self) -> List[Dict]:
        if not self.use_playwright:
             raise RuntimeError("OpenAI scraper requires Playwright")

        self.logger.info(f"Navigating to {self.base_url}")
        page = await self.context.new_page()
        page.set_default_timeout(self.timeout)
        
        scraped_date = datetime.now(timezone.utc).isoformat()

        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=self.timeout)
            
            # Wait for content
            await page.wait_for_selector('main', state="visible", timeout=15000) 
            await page.wait_for_selector('a[href*="/research/"]', state="visible", timeout=10000)
            await page.wait_for_timeout(3000) 

            results = await page.evaluate("""() => {
                const items = [];
                const links = Array.from(document.querySelectorAll('a'));
                
                links.forEach(link => {
                    const href = link.href;
                    if (href.includes('/research/') || href.includes('/index') || href.includes('.pdf') || href.includes('arxiv.org')) {
                        const title = link.innerText.trim();
                        if (title.length > 10 && !title.includes("Sign up") && !title.includes("Login")) {
                             items.push({
                                 title: title,
                                 url: href,
                                 date: "Unknown" 
                             });
                        }
                    }
                });
                
                // Filter duplicates
                const unique = [];
                const seen = new Set();
                items.forEach(i => {
                    if (!seen.has(i.url)) {
                        seen.add(i.url);
                        unique.push(i);
                    }
                });
                return unique;
            }""")
            
            self.logger.info(f"Found {len(results)} potential research items.")
            
            for res in results:
                res['published_date'] = None 
                res['scraped_date'] = scraped_date

            return results

        except Exception as e:
            self.logger.error(f"Error scraping OpenAI Research: {e}")
            await page.screenshot(path="openai_error.png")
            return []
        finally:
            await page.close()
