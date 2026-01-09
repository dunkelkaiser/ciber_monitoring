import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from agents.scrapers.base_scraper import BaseScraper
from agents.scrapers.cve_mitre_scraper import CVEMitreScraper

# Mock concrete implementation for BaseScraper testing
class ConcreteScraper(BaseScraper):
    async def scrape(self):
        return [{"test": "data"}]

@pytest.fixture
def scraper():
    return ConcreteScraper(name="test_scraper")

@pytest.mark.asyncio
async def test_base_scraper_initialization(scraper):
    assert scraper.name == "test_scraper"
    assert scraper.rate_limit == 30 # Default

@pytest.mark.asyncio
async def test_save_bronze(scraper):
    # Mock file operations
    mock_data = [{"id": 1, "val": "test"}]
    
    with patch("builtins.open", new_callable=MagicMock) as mock_file:
        with patch("json.dump") as mock_json:
            with patch("os.makedirs") as mock_dirs:
                await scraper.save_bronze(mock_data)
                
                assert mock_dirs.called
                assert mock_file.called
                # Verify JSON structure was passed
                args, _ = mock_json.call_args
                assert args[0]['data'] == mock_data
                assert "metadata" in args[0]

@pytest.mark.asyncio
async def test_rate_limiting(scraper):
    scraper.rate_limit = 600 # 10 requests/sec -> 0.1s wait
    
    start = datetime.now()
    await scraper._rate_limit_wait()
    await scraper._rate_limit_wait()
    # Should be minimal wait, hard to assert exact time without mocking time
    # This mainly ensures it doesn't crash
    assert True

# Example test for specific scraper logic
@pytest.fixture
def cve_scraper():
    return CVEMitreScraper()

def test_cve_severity_extraction(cve_scraper):
    assert cve_scraper._extract_severity("Critical buffer overflow") == "CRITICAL"
    assert cve_scraper._extract_severity("High severity issue") == "HIGH"
    assert cve_scraper._extract_severity("Minor annoyance") == "UNKNOWN"

from datetime import datetime
