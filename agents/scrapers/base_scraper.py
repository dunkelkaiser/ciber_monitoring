import abc
import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log")
    ]
)

class BaseScraper(ABC):
    """
    Abstract base class for all web scrapers.
    Implements shared functionality: anti-bot, rate limiting, retries, persistence.
    """

    def __init__(
        self,
        name: str,
        config_path: str = "config.yaml",
        output_dir: str = "C:/Users/jagua/OneDrive/Documentos/Diplomado IA y TA/Modulo 4  Proyecto Integrador/ciber_monitoring/data_engineering/bronze"
    ):
        self.name = name
        self.output_dir = output_dir
        self.logger = logging.getLogger(name)
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.scraper_config = self.config.get('scrapers', {}).get(name, {})
        
        # Scraper settings
        self.rate_limit = self.scraper_config.get('rate_limit', 30)
        self.use_playwright = self.scraper_config.get('use_playwright', False)
        self.user_agents = self.config.get('system', {}).get('user_agents', [])
        
        # State
        self.last_request_time = 0
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

    def _load_config(self, path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def _get_random_user_agent(self) -> str:
        """Return a random user agent from the pool."""
        if not self.user_agents:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        return random.choice(self.user_agents)

    async def _rate_limit_wait(self):
        """Enforce rate limits by sleeping if necessary."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 60.0 / self.rate_limit
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

    async def _setup_playwright(self):
        """Initialize Playwright with stealth settings."""
        if not self.use_playwright:
            return

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Create context with random user agent and viewport
        user_agent = self._get_random_user_agent()
        viewport = {
            'width': 1920 + random.randint(-100, 100),
            'height': 1080 + random.randint(-100, 100)
        }
        
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale='en-US'
        )
        
        # Add stealth scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    async def _teardown_playwright(self):
        """Clean up Playwright resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _get_httpx_client(self) -> httpx.AsyncClient:
        """Create a configured httpx client."""
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        return httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)))
    async def _fetch_url(self, url: str) -> str:
        """Fetch URL with retries and rate limiting using httpx."""
        await self._rate_limit_wait()
        async with self._get_httpx_client() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def save_bronze(self, data: List[Dict]):
        """Save extracted data to Bronze layer (JSON)."""
        if not data:
            self.logger.warning("No data to save.")
            return

        timestamp = datetime.now().isoformat().replace(':', '-')
        filename = f"{self.name}_raw_{timestamp}.json"
        
        # Ensure directory exists
        try:
            # Handle absolute paths vs relative paths correctly
            if os.path.isabs(self.output_dir):
                target_dir = self.output_dir
            else:
                 # Ensure we are saving where intended relative to current execution context if mocked, 
                 # but usually output_dir from config should be respected.
                 # Given the user request, let's assume local relative path for now or absolute from config.
                 target_dir = self.output_dir
            
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            
            output_record = {
                "metadata": {
                    "source": self.name,
                    "timestamp": datetime.now().isoformat(),
                    "record_count": len(data)
                },
                "data": data
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_record, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(data)} records to {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")

    async def run(self):
        """Main execution method."""
        self.logger.info(f"Starting scraper: {self.name}")
        try:
            if self.use_playwright:
                await self._setup_playwright()
            
            data = await self.scrape()
            await self.save_bronze(data)
            
        except Exception as e:
            self.logger.error(f"Scraper failed: {e}", exc_info=True)
        finally:
            if self.use_playwright:
                await self._teardown_playwright()
            self.logger.info(f"Finished scraper: {self.name}")

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """Core scraping logic to be implemented by child classes."""
        pass
