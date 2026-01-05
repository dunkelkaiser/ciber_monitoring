from typing import List, Dict
from bs4 import BeautifulSoup
import re
from base_scraper import BaseScraper

class CVEMitreScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="cve_mitre")
        self.base_url = self.scraper_config.get("base_url")
        self.keywords = self.scraper_config.get("keywords", [])

    async def scrape(self) -> List[Dict]:
        results = []
        for keyword in self.keywords:
            self.logger.info(f"Searching for keyword: {keyword}")
            try:
                # Construct search URL
                url = f"{self.base_url}?keyword={keyword}"
                html = await self._fetch_url(url)
                
                # Parse HTML
                soup = BeautifulSoup(html, 'lxml')
                table = soup.find('div', id='TableWithRules')
                
                if not table:
                    self.logger.warning(f"No results table found for {keyword}")
                    continue

                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 2:
                        continue
                        
                    cve_id = cols[0].text.strip()
                    description = cols[1].text.strip()
                    
                    # Basic extraction logic
                    entry = {
                        "cve_id": cve_id,
                        "description": description,
                        "source_url": url,
                        "keyword_matched": keyword,
                        "severity": self._extract_severity(description),
                        "published_date": "N/A",  # Mitre search results don't always show date
                        "affected_products": self._extract_products(description)
                    }
                    results.append(entry)
                    
            except Exception as e:
                self.logger.error(f"Error searching for {keyword}: {e}")
                
        return results

    def _extract_severity(self, text: str) -> str:
        text_lower = text.lower()
        if "critical" in text_lower:
            return "CRITICAL"
        if "high" in text_lower:
            return "HIGH"
        if "medium" in text_lower:
            return "MEDIUM"
        if "low" in text_lower:
            return "LOW"
        return "UNKNOWN"

    def _extract_products(self, text: str) -> List[str]:
        # Simple heuristic to extract product names (often at start of desc)
        # In real scenario, would use NER
        return []
