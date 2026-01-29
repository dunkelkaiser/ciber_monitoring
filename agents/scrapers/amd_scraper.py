from typing import List, Dict
from base_scraper import BaseScraper
from datetime import datetime, timezone
import asyncio
from bs4 import BeautifulSoup
import re

class AMDScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="amd")
        self.base_url = self.scraper_config.get("base_url", "https://www.amd.com/en/resources/product-security.html")

    async def scrape(self) -> List[Dict]:
        """
        Scrapes AMD Product Security Bulletins.
        Prioritizes a lightweight fetch approach (httpx + BeautifulSoup) for robustness,
        with an optional fallback or enrichment using Playwright if enabled/needed.
        """
        results = []
        scraped_date = datetime.now(timezone.utc).isoformat()
        
        try:
            self.logger.info(f"Fetching AMD security page: {self.base_url}")
            # Use BaseScraper's lightweight fetch (httpx)
            html_content = await self._fetch_url(self.base_url)
            
            if not html_content:
                self.logger.error("Failed to retrieve HTML content from AMD")
                return []

            soup = BeautifulSoup(html_content, 'html.parser')
            
            # AMD security page often lists items in a table or a list of links
            # Strategy 1: Look for links with "amd-sb-" in the href
            bulletin_links = soup.find_all('a', href=re.compile(r'/bulletin/amd-sb-'))
            
            if bulletin_links:
                self.logger.info(f"Found {len(bulletin_links)} bulletin links via BeautifulSoup")
                for link in bulletin_links:
                    title = link.get_text(strip=True)
                    href = link.get('href')
                    
                    if not title or not href:
                        continue

                    # Construct full URL
                    full_url = href if href.startswith('http') else f"https://www.amd.com{href}"
                    
                    # Extract Advisory ID from URL
                    # e.g., /en/resources/product-security/bulletin/amd-sb-7055.html -> AMD-SB-7055
                    match = re.search(r'amd-sb-\d+', href.lower())
                    advisory_id = match.group(0).upper() if match else "AMD-SB-UNKNOWN"

                    results.append({
                        "advisory_id": advisory_id,
                        "title": title,
                        "source_url": full_url,
                        "scraped_date": scraped_date,
                        "vendor": "AMD",
                        "published_date": datetime.now().strftime("%Y-%m-%d"), # Fallback to today
                        "severity": "High", # Default for security bulletins
                    })
            
            # Strategy 2: Table parsing (if available in the HTML dump)
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if not rows: continue
                
                # Check headers to see if it's the right table
                headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
                if any(h in ['id', 'bulletin', 'advisory'] for h in headers) and 'title' in headers:
                    self.logger.info("Found security bulletin table, parsing...")
                    for row in rows[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            texts = [c.get_text(strip=True) for c in cols]
                            entry = {
                                "advisory_id": texts[0],
                                "title": texts[1],
                                "published_date": texts[2] if len(texts) > 2 else None,
                                "severity": texts[3] if len(texts) > 3 else "High",
                                "source_url": self.base_url, # Default to main page
                                "scraped_date": scraped_date,
                                "vendor": "AMD"
                            }
                            # Check if the title has a link
                            link_elem = cols[1].find('a')
                            if link_elem and link_elem.get('href'):
                                l = link_elem.get('href')
                                entry["source_url"] = l if l.startswith('http') else f"https://www.amd.com{l}"
                            
                            results.append(entry)

        except Exception as e:
            self.logger.error(f"Error during lightweight AMD scraping: {e}")
            
            # Final Fallback to Playwright only if lightweight failed and use_playwright is True
            if self.use_playwright:
                self.logger.info("Attempting Playwright fallback for AMD...")
                results = await self._scrape_playwright(scraped_date)

        # Deduplicate results based on advisory_id
        unique_results = {}
        for r in results:
            aid = r.get('advisory_id', 'unknown')
            unique_results[aid] = r
            
        return list(unique_results.values())

    async def _scrape_playwright(self, scraped_date: str) -> List[Dict]:
        """Legacy/Fallback Playwright logic."""
        results = []
        page = await self.context.new_page()
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5) # Allow dynamic content
            
            links = await page.locator("a[href*='/bulletin/amd-sb-']").all()
            for link in links:
                title = await link.inner_text()
                href = await link.get_attribute("href")
                if title and href:
                    match = re.search(r'amd-sb-\d+', href.lower())
                    advisory_id = match.group(0).upper() if match else "AMD-SB-UNKNOWN"
                    results.append({
                        "advisory_id": advisory_id,
                        "title": title.strip(),
                        "source_url": f"https://www.amd.com{href}" if href.startswith('/') else href,
                        "published_date": datetime.now().strftime("%Y-%m-%d"),
                        "severity": "High",
                        "scraped_date": scraped_date,
                        "vendor": "AMD"
                    })
        except Exception as e:
            self.logger.error(f"Playwright fallback failed: {e}")
        finally:
            await page.close()
        return results
