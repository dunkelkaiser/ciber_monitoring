from typing import List, Dict
from base_scraper import BaseScraper
from datetime import datetime, timezone

class IntelScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="intel")
        self.base_url = self.scraper_config.get("base_url")

    async def scrape(self) -> List[Dict]:
        if not self.use_playwright:
             raise RuntimeError("Intel scraper requires Playwright")

        results = []
        page = await self.context.new_page()
        
        scraped_date = datetime.now(timezone.utc).isoformat()
        
        try:
            self.logger.info(f"Navigating to {self.base_url}")
            await page.goto(self.base_url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            
            # Intel often uses intricate JS tables
            # This is a placeholder for the specific table selector logic
            # Assuming a standard table structure for the example
            
            # Wait for table
            await page.wait_for_selector("table", timeout=10000)
            
            rows = await page.locator("table tr").all()
            
            for row in rows[1:]:
                cols = await row.locator("td").all()
                if not cols:
                    continue
                    
                # Clean extraction
                texts = [await c.inner_text() for c in cols]
                
                # Naive mapping based on typical security table columns
                # ID | Title | Date | Severity
                if len(texts) >= 4:
                    # Attempt to parse date from texts[2]
                    raw_date = texts[2].strip()
                    # Keep raw, but also put in published_date if parsable
                    
                    results.append({
                        "advisory_id": texts[0].strip(),
                        "title": texts[1].strip(),
                        "date": raw_date,
                        "severity": texts[3].strip(),
                        "source_url": self.base_url,
                        "published_date": raw_date, # Ideally parse to ISO
                        "scraped_date": scraped_date
                    })

        except Exception as e:
            self.logger.error(f"Error scraping Intel: {e}")
        finally:
            await page.close()
            
        return results
