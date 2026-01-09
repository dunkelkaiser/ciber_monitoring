from typing import List, Dict
from base_scraper import BaseScraper
import asyncio

class NVIDIAScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="nvidia")
        self.base_url = self.scraper_config.get("base_url", "https://www.nvidia.com/en-us/research/publications/")
        self.timeout = self.scraper_config.get("timeout", 60000)

    async def scrape(self) -> List[Dict]:
        if not self.use_playwright:
             raise RuntimeError("NVIDIA scraper requires Playwright")

        self.logger.info(f"Navigating to {self.base_url}")
        page = await self.context.new_page()
        page.set_default_timeout(self.timeout)
        
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=self.timeout)
            # Wait for list or table
            # Nvidia publications page usually has a filterable list.
            await page.wait_for_selector('body', timeout=15000)
            await page.wait_for_load_state("networkidle")

            results = await page.evaluate("""() => {
                const items = [];
                // Look for publication links
                // Often they link to .pdf or specific pages.
                
                // Strategy: Find all links that look like titles of papers.
                const links = Array.from(document.querySelectorAll('a'));
                
                links.forEach(link => {
                    const href = link.href;
                    const text = link.innerText.trim();
                    
                    // Filter logic: Nvidia links often contain 'research.nvidia.com' or are PDFs
                    // Or they are just relative links in the publications section.
                    if (text.length > 15 && (href.includes('.pdf') || href.includes('/research/'))) {
                         items.push({
                             title: text,
                             url: href,
                             type: "Research Publication"
                         });
                    }
                });
                
                // De-duplicate
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
            return results

        except Exception as e:
            self.logger.error(f"Error scraping NVIDIA Research: {e}")
            await page.screenshot(path="nvidia_error.png")
            return []
        finally:
            await page.close()
