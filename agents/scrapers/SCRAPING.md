# 🕷️ Web Scraping System - MVP Implementation Guide

## Objective
Develop an object-oriented web scraping system with a base parent class that encapsulates common functionality. Child scrapers should inherit shared modules and only implement custom logic when necessary.

---

## Tech Stack (MVP)
```python
playwright==1.40.0          # Anti-bot capability
httpx==0.25.2              # Lightweight HTTP client
beautifulsoup4==4.12.2     # HTML parsing
lxml==4.9.3                # Fast XML/HTML parser
python-dotenv==1.0.0       # Environment variables
```

---

## Architecture Overview

```
BaseScraper (Abstract Parent Class)
    ↓
    ├── Common Modules:
    │   ├── Anti-bot evasion
    │   ├── Rate limiting
    │   ├── Retry logic
    │   ├── Data persistence (Bronze layer)
    │   ├── Logging
    │   └── Error handling
    ↓
Child Scrapers (Specific Implementations)
    ├── CVEMitreScraper
    ├── NVIDIAScraper
    ├── IntelScraper
    ├── TwitterScraper
    └── OpenAIBlogScraper
```

---

## Implementation Instructions

### 1. Create Base Scraper Class

**File**: `scrapers/base_scraper.py`

**Requirements**:
- Must be an **abstract base class** using `ABC` from `abc` module
- Define abstract method `scrape()` that child classes must implement
- Include the following **shared modules**:

#### Shared Modules to Implement:

**A. Anti-Bot Evasion**
- Random user-agent rotation from a predefined list
- Random delays between requests (1-3 seconds)
- Browser fingerprint masking for Playwright
- Cloudflare bypass capabilities

**B. Rate Limiting**
- Configurable requests per minute (default: 30)
- Automatic delay calculation between requests
- Queue system for managing request timing

**C. Retry Logic**
- Exponential backoff for failed requests (3 retries max)
- Different handling for HTTP errors (4xx vs 5xx)
- Timeout configuration (30 seconds default)

**D. Data Persistence**
- Method `save_bronze()` that:
  - Creates JSON files in Bronze layer directory
  - Includes metadata: source name, timestamp, scraper version
  - Uses ISO format timestamps in filenames
  - Handles file path creation automatically

**E. Logging**
- Structured logging with levels: DEBUG, INFO, WARNING, ERROR
- Log format: `[TIMESTAMP] [SCRAPER_NAME] [LEVEL] Message`
- Separate log files per scraper
- Console output for real-time monitoring

**F. Error Handling**
- Try-catch wrappers for common exceptions
- Graceful degradation (continue on partial failures)
- Error notification system (log + optional alert)

#### Constructor Parameters:
```python
def __init__(
    self,
    output_dir: str = '/data/bronze',
    rate_limit: int = 30,  # requests per minute
    max_retries: int = 3,
    timeout: int = 30,
    use_playwright: bool = False
)
```

#### Required Methods:
- `scrape()` - Abstract method, must be implemented by children
- `save_bronze(data: List[Dict], source_name: str)` - Save to Bronze layer
- `_get_random_user_agent()` - Return random UA string
- `_rate_limit_wait()` - Sleep to respect rate limits
- `_retry_request(func, *args, **kwargs)` - Retry wrapper with backoff
- `_setup_playwright_browser()` - Initialize Playwright with anti-detection
- `_setup_httpx_client()` - Initialize httpx with proper headers

---

### 2. Implement Specific Scrapers

Each scraper should inherit from `BaseScraper` and **only** implement:
1. The `scrape()` method with source-specific logic
2. Custom parsing methods if needed
3. Source-specific configurations

---

#### **Scraper 1: CVE Mitre**

**File**: `scrapers/agents/cve_mitre_scraper.py`

**Source**: `https://cve.mitre.org/cgi-bin/cvekey.cgi`

**Approach**: Use `httpx` (no anti-bot needed, API-friendly)

**Data to Extract**:
- CVE ID
- Description
- Publication date
- Severity (extract from description text)
- Affected products

**Custom Logic**:
- Search keywords: "artificial intelligence", "GPU", "neural network"
- Parse HTML table structure
- Extract severity from description using keyword matching

**Expected Output Schema**:
```json
{
  "cve_id": "CVE-2024-1234",
  "description": "Buffer overflow in...",
  "published_date": "2024-01-15",
  "severity": "HIGH",
  "affected_products": ["NVIDIA Driver", "CUDA"],
  "source_url": "https://cve.mitre.org/..."
}
```

---

#### **Scraper 2: NVIDIA Security**

**File**: `scrapers/agents/nvidia_scraper.py`

**Source**: `https://www.nvidia.com/en-us/security/`

**Approach**: Use `Playwright` (Cloudflare protected)

**Data to Extract**:
- Security bulletin ID
- Title
- Publication date
- Severity rating
- CVE references
- Affected products

**Custom Logic**:
- Use Playwright with stealth mode
- Scroll page to trigger lazy loading
- Wait for dynamic content (network idle)
- Parse bulletin cards from JavaScript-rendered content

**Anti-Bot Specific**:
- Add random mouse movements
- Random scroll patterns
- Wait 2-4 seconds between actions

**Expected Output Schema**:
```json
{
  "bulletin_id": "NVIDIA-2024-001",
  "title": "Security Update for...",
  "date": "2024-01-10",
  "severity": "CRITICAL",
  "cves": ["CVE-2024-5678", "CVE-2024-5679"],
  "products": ["GeForce Driver", "RTX"],
  "bulletin_url": "https://nvidia.com/..."
}
```

---

#### **Scraper 3: Intel Security Center**

**File**: `scrapers/agents/intel_scraper.py`

**Source**: `https://www.intel.com/content/www/us/en/security-center/default.html`

**Approach**: Use `Playwright` (JavaScript-heavy page)

**Data to Extract**:
- Advisory ID
- Title
- Severity
- CVE IDs
- Date published
- Affected products

**Custom Logic**:
- Similar to NVIDIA scraper
- Handle Intel-specific HTML structure
- Extract from security advisories table

**Expected Output Schema**:
```json
{
  "advisory_id": "INTEL-SA-00123",
  "title": "Potential Security Vulnerabilities...",
  "severity": "HIGH",
  "cves": ["CVE-2024-9999"],
  "date": "2024-01-12",
  "products": ["Intel Core Processors"],
  "advisory_url": "https://intel.com/..."
}
```

---

#### **Scraper 4: Twitter/X (Social Intelligence)**

**File**: `scrapers/agents/twitter_scraper.py`

**Source**: Twitter API v2

**Approach**: Use official API (no scraping needed)

**API Requirements**:
- Bearer token from environment variable: `TWITTER_BEARER_TOKEN`
- Use `tweepy` library

**Search Queries**:
```python
queries = [
    'CVE vulnerability -is:retweet lang:en',
    'zero-day exploit -is:retweet lang:en',
    'NVIDIA security -is:retweet lang:en',
    'Intel vulnerability -is:retweet lang:en'
]
```

**Data to Extract**:
- Tweet ID
- Text content
- Author username
- Creation timestamp
- Engagement metrics (likes, retweets)
- Query keyword that matched

**Custom Logic**:
- Iterate through multiple queries
- Fetch 100 recent tweets per query
- Deduplicate by tweet ID
- Extract mentioned CVE IDs from text using regex

**Expected Output Schema**:
```json
{
  "tweet_id": "1234567890",
  "text": "New CVE-2024-1234 affects...",
  "author": "securityresearcher",
  "created_at": "2024-01-15T10:30:00Z",
  "likes": 42,
  "retweets": 15,
  "query": "CVE vulnerability",
  "mentioned_cves": ["CVE-2024-1234"]
}
```

---

#### **Scraper 5: OpenAI Blog**

**File**: `scrapers/agents/openai_blog_scraper.py`

**Source**: `https://openai.com/blog`

**Approach**: Use `Playwright` (dynamic loading)

**Data to Extract**:
- Article title
- Publication date
- Author
- Article excerpt/summary
- Full URL
- Tags/categories

**Custom Logic**:
- Scroll to load more articles
- Click "Load More" button if present
- Extract articles from blog grid
- Filter for security-related keywords

**Expected Output Schema**:
```json
{
  "title": "GPT-4 Security Update",
  "date": "2024-01-08",
  "author": "OpenAI Team",
  "excerpt": "We've implemented new safety measures...",
  "url": "https://openai.com/blog/gpt4-security",
  "tags": ["security", "gpt-4"]
}
```

---

### 3. Create Orchestrator

**File**: `scrapers/orchestrator.py`

**Purpose**: Coordinate all scrapers to run sequentially or in parallel

**Requirements**:
- Import all child scrapers
- Run scrapers with proper error isolation (one failure doesn't stop others)
- Collect and aggregate results
- Generate summary report
- Support CLI arguments:
  - `--initial-load`: Run all scrapers immediately
  - `--scraper=name`: Run specific scraper only
  - `--parallel`: Run scrapers concurrently

**Implementation Pattern**:
```python
async def run_all_scrapers(parallel=False):
    scrapers = [
        CVEMitreScraper(),
        NVIDIAScraper(),
        IntelScraper(),
        TwitterScraper(),
        OpenAIBlogScraper()
    ]
    
    if parallel:
        # Use asyncio.gather with exception handling
        pass
    else:
        # Run sequentially
        pass
    
    # Generate summary report
    # Log success/failure for each scraper
```

---

### 4. Docker Configuration

**File**: `scrapers/Dockerfile`

**Requirements**:
- Base image: `python:3.11-slim`
- Install Playwright browsers
- Install all dependencies from `requirements.txt`
- Set working directory to `/app`
- Copy scraper code
- Set environment variable `PYTHONUNBUFFERED=1`

**File**: `docker-compose.yml` (scraper services section)

Create separate service for each scraper:
```yaml
scraper-cve:
  build: ./scrapers
  environment:
    - TARGET=cve_mitre
    - SCHEDULE=0 */6 * * *  # Every 6 hours
  volumes:
    - ./data/bronze:/data/bronze

scraper-nvidia:
  build: ./scrapers
  environment:
    - TARGET=nvidia
    - SCHEDULE=0 8 * * *    # Daily at 8am
  volumes:
    - ./data/bronze:/data/bronze

# ... similar for other scrapers
```

---

### 5. Configuration Management

**File**: `scrapers/config.yaml`

Define scraper-specific configurations:
```yaml
scrapers:
  cve_mitre:
    rate_limit: 30
    use_playwright: false
    keywords: ["AI", "GPU", "neural network"]
  
  nvidia:
    rate_limit: 20
    use_playwright: true
    timeout: 60
  
  intel:
    rate_limit: 20
    use_playwright: true
    timeout: 60
  
  twitter:
    rate_limit: 180  # Twitter API limit
    max_results: 100
  
  openai:
    rate_limit: 30
    use_playwright: true
```

---

### 6. Testing Requirements

**File**: `tests/test_scrapers.py`

Create unit tests for:
- Base class initialization
- Rate limiting functionality
- Retry logic with mock failures
- Data persistence (check JSON file creation)
- Each scraper's `scrape()` method with mock data

**Testing Pattern**:
```python
def test_base_scraper_rate_limiting():
    # Test that requests respect rate limits
    pass

def test_cve_scraper_parsing():
    # Mock HTML response, test parsing logic
    pass

def test_nvidia_scraper_playwright():
    # Test Playwright initialization
    pass
```

---

## Execution Flow

```
1. User runs: python scrapers/orchestrator.py --initial-load

2. Orchestrator initializes all scrapers

3. Each scraper:
   a. Inherits BaseScraper capabilities
   b. Configures source-specific settings
   c. Executes scrape() method
   d. Data is automatically saved to Bronze layer
   e. Logs are written to console and file

4. Orchestrator generates summary:
   - Total records scraped per source
   - Success/failure status
   - Execution time per scraper
   - Errors encountered

5. Bronze layer now contains:
   /data/bronze/
     ├── bronze_cve_mitre_2024-01-15T10:30:00.json
     ├── bronze_nvidia_2024-01-15T10:32:00.json
     ├── bronze_intel_2024-01-15T10:35:00.json
     ├── bronze_twitter_2024-01-15T10:38:00.json
     └── bronze_openai_2024-01-15T10:40:00.json
```

---

## Anti-Bot Best Practices (Implementation Checklist)

For **Playwright-based scrapers** (NVIDIA, Intel, OpenAI):

- [ ] Randomize viewport size (1920x1080 ± 100px)
- [ ] Rotate user agents from real browser list
- [ ] Add random delays between page actions (1-3 seconds)
- [ ] Implement random mouse movements before clicks
- [ ] Scroll page in random increments (not full page jumps)
- [ ] Wait for `networkidle` state before extracting
- [ ] Disable `navigator.webdriver` property
- [ ] Use stealth plugin or manual fingerprint masking
- [ ] Respect `robots.txt` (check before scraping)
- [ ] Implement exponential backoff on 429 errors

For **httpx-based scrapers** (CVE Mitre):

- [ ] Rotate user agents
- [ ] Add realistic headers (Accept, Accept-Language, etc.)
- [ ] Respect rate limits from response headers
- [ ] Use connection pooling
- [ ] Handle redirects gracefully

---

## Expected Deliverables

1. ✅ `base_scraper.py` - Fully functional parent class with all shared modules
2. ✅ 5 child scraper files - Each implementing only custom logic
3. ✅ `orchestrator.py` - Coordination script with CLI support
4. ✅ `Dockerfile` - Container definition with Playwright
5. ✅ `docker-compose.yml` - Service definitions for each scraper
6. ✅ `config.yaml` - Centralized configuration
7. ✅ `tests/test_scrapers.py` - Unit tests for all components
8. ✅ Bronze layer populated with JSON files

---

## Success Criteria

- [ ] All 5 scrapers run without errors
- [ ] Data is saved to Bronze layer in correct JSON format
- [ ] Anti-bot evasion works for protected sites (no 403/429 errors)
- [ ] Rate limiting prevents server overload
- [ ] Logs provide clear visibility into scraping process
- [ ] Docker containers start and execute successfully
- [ ] At least 80% code coverage in tests
- [ ] No code duplication between scrapers (shared logic in base class)

---

## Code Quality Standards

- Use **type hints** for all function parameters and return values
- Follow **PEP 8** style guide
- Maximum line length: 100 characters
- Docstrings for all classes and public methods (Google style)
- Use `async/await` for asynchronous scrapers
- Handle all exceptions explicitly (no bare `except:`)
- Use f-strings for string formatting
- Use context managers (`with` statements) for file operations

---

## Example Usage

```python
# Run all scrapers sequentially
python scrapers/orchestrator.py --initial-load

# Run specific scraper
python scrapers/orchestrator.py --scraper=nvidia

# Run all in parallel (faster but more resource intensive)
python scrapers/orchestrator.py --parallel

# Docker execution
docker-compose up scraper-nvidia
```

---

## Monitoring and Maintenance

- Check logs daily: `tail -f logs/scrapers.log`
- Monitor Bronze layer size: Implement cleanup for files older than 30 days
- Update user agent list monthly
- Test scrapers weekly to catch website structure changes
- Set up alerts for scraper failures (email/Slack notification)

---

## Notes

- This is an **MVP implementation** - focus on functionality over perfection
- Prioritize **code reusability** through inheritance
- Test with small datasets first before full scraping runs
- Respect website terms of service and robots.txt
- For production, add proxy rotation and CAPTCHA solving services