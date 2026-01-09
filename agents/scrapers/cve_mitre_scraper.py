from typing import List, Dict
from bs4 import BeautifulSoup
import re
from base_scraper import BaseScraper
import asyncio

class CVEMitreScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="cve_mitre")
        self.base_url = self.scraper_config.get("base_url")
        self.keywords = self.scraper_config.get("keywords", [])
        self.timeout = self.scraper_config.get("timeout", 60000)

    async def scrape(self) -> List[Dict]:
        if not self.use_playwright:
             raise RuntimeError("CVE Mitre (cve.org) scraper requires Playwright")

        results = []
        page = await self.context.new_page()
        
        for keyword in self.keywords:
            self.logger.info(f"Searching for keyword: {keyword}")
            try:
                # Construct search URL for cve.org
                url = f"{self.base_url}?query={keyword}"
                self.logger.info(f"Navigating to {url}")
                
                # Navigate
                page.set_default_timeout(self.timeout)
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
                
                # Wait for at least one result link to appear. 
                # This guarantees that the App has rendered the results.
                # Use a try/except to capture screenshot if it fails (e.g. 0 results)
                try:
                    # Wait for ANY CVE link
                    await page.wait_for_selector("a[href*='/CVERecord?id=']", state="visible", timeout=15000) 
                except Exception as wait_err:
                    self.logger.warning(f"No results found (or timeout) for {keyword}. taking debug screenshot.")
                    await page.screenshot(path=f"cve_debug_{keyword}.png")
                    continue

                # Use JS evaluation to parse the visual structure of rows
                # We select ALL rows with class 'columns cve-columns'
                page_results = await page.evaluate("""() => {
                    const allRows = Array.from(document.querySelectorAll('.columns.cve-columns')); 
                    const items = [];
                    let current = {};
                    
                    allRows.forEach(row => {
                        // Look for CVE ID link
                        const link = row.querySelector("a[href*='/CVERecord?id=']");
                        if (link) {
                            // If we have a pending item, push it
                            if (current.cve_id) items.push(current);
                            
                            // Start new item
                            current = {
                                cve_id: link.innerText.trim(),
                                source_url: link.href,
                                description: "No description found"
                            };
                        }
                        
                        // Look for description in this row OR if this row IS the description row
                        const paragraphs = row.querySelectorAll("p");
                        paragraphs.forEach(p => {
                            const t = p.innerText.trim();
                            // Simple heuristic to identify description text
                            if (t && !t.startsWith("CNA:") && !t.includes("Showing") && !t.includes("Sort by") && !t.startsWith("CVE ID")) {
                                if (current.cve_id && current.description === "No description found") {
                                     current.description = t;
                                }
                            }
                        });
                    });
                    
                    // Push the last one
                    if (current.cve_id) items.push(current);
                    return items;
                }""")
                
                self.logger.info(f"Found {len(page_results)} results for {keyword}")
                
                # Post-process
                for item in page_results:
                    item['keyword_matched'] = keyword
                    item['severity'] = "UNKNOWN" 
                    item['published_date'] = "UNKNOWN"
                    item['affected_products'] = []
                    results.append(item)
                    
            except Exception as e:
                self.logger.error(f"Error searching for {keyword}: {e}")
                await page.screenshot(path=f"cve_error_{keyword}.png")
                
        await page.close()
        return results
