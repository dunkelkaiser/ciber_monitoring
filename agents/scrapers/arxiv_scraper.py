from typing import List, Dict
import arxiv
from datetime import datetime, timezone
from base_scraper import BaseScraper

class ArxivScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="arxiv")
        self.categories = self.scraper_config.get("categories", ["cs.CR"])
        self.keywords = self.scraper_config.get("keywords", ["security"])
        self.max_results = self.scraper_config.get("max_results", 50)

    async def scrape(self) -> List[Dict]:
        results = []
        scraped_date = datetime.now(timezone.utc).isoformat()
        
        # Construct query: (cat:cs.CR OR cat:cs.AI) AND (all:security OR all:LLM)
        # Verify arxiv query syntax. Usually simple OR/AND works.
        
        # Let's do simple queries for each category + keyword combination to ensure coverage
        # Or construct a big query string.
        
        # "cat:cs.CR AND (security OR vulnerability)"
        
        joined_keywords = " OR ".join([f'all:"{k}"' for k in self.keywords])
        joined_categories = " OR ".join([f'cat:{c}' for c in self.categories])
        
        query = f"({joined_categories}) AND ({joined_keywords})"
        
        self.logger.info(f"Querying arXiv with: {query}")

        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )

            # arxiv client is synchronous iterator, but robust.
            for result in client.results(search):
                
                published_date = result.published.isoformat() if result.published else None
                
                paper_data = {
                    "title": result.title,
                    "abstract": result.summary,
                    "authors": [a.name for a in result.authors],
                    "categories": result.categories,
                    "url": result.entry_id,
                    "pdf_url": result.pdf_url,
                    "arxiv_id": result.entry_id.split('/')[-1],
                    "published_date": published_date,
                    "scraped_date": scraped_date,
                    "source": "arxiv"
                }
                results.append(paper_data)

        except Exception as e:
            self.logger.error(f"Error querying arXiv: {e}")

        self.logger.info(f"Collected {len(results)} papers from arXiv.")
        return results
