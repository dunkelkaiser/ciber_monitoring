from typing import List, Dict
import os
import time
import json
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from base_scraper import BaseScraper

# Load env from local directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class RedditScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="reddit")
        self.email = "balamsinhue@gmail.com"
        self.password = os.getenv("PASS_GMAIL")
        self.subreddits = ["cybersecurity", "intel", "amd", "nvidia", "hardware"] 
        self.driver = None

    def setup_driver(self):
        chrome_options = Options()
        # chrome_options.add_argument("--headless=new") # Commented out for debugging login if needed
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--start-maximized")
        # Try to avoid detection
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def login_google(self):
        self.logger.info("Starting Google Login Flow...")
        self.driver.get("https://www.reddit.com/login/")
        time.sleep(5) # Wait for load
        
        try:
            # Strategy 1: Main DOM Button (New UI often uses <shreddit-async-loader> or Shadow DOM, but usually inputs are in light DOM)
            # Look for any element "Continue with Google"
            self.logger.info("Comparing selectors...")
            
            google_btn = None
            
            # Simple Text Search first
            try:
                # Common XPaths
                xpaths = [
                    "//button[contains(., 'Continue with Google')]",
                    "//div[contains(., 'Continue with Google') and @role='button']",
                    "//span[contains(., 'Continue with Google')]",
                    "//*[contains(text(), 'Google')]"
                ]
                
                for xpath in xpaths:
                    try:
                        google_btn = self.driver.find_element(By.XPATH, xpath)
                        if google_btn.is_displayed():
                            self.logger.info(f"Found Google button with XPath: {xpath}")
                            break
                        else:
                            google_btn = None
                    except:
                        continue
            except:
                pass

            # Strategy 2: Iframe (Old UI or embedded OneTap)
            if not google_btn:
                self.logger.info("Checking iframes...")
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for ifr in iframes:
                    src = ifr.get_attribute("src") or ""
                    if "accounts.google.com" in src or "gsi" in src:
                        self.logger.info(f"Switching to Google Iframe: {src[:50]}...")
                        self.driver.switch_to.frame(ifr)
                        try:
                            google_btn = self.driver.find_element(By.XPATH, "//*[@role='button'] | //div[contains(@id, 'google')]")
                            self.logger.info("Found button inside iframe.")
                            break
                        except:
                            self.driver.switch_to.default_content()

            if not google_btn:
                # Last resort: Shadow DOM or specific Reddit custom element
                # Attempt to dump page source for debugging
                with open("login_page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                raise Exception("Could not find Google Login button. Page source saved.")

            # Click
            google_btn.click()
            self.logger.info("Clicked Google Button. Waiting for Popup...")
            
            # Switch to popup
            time.sleep(3)
            window_handles = self.driver.window_handles
            self.driver.switch_to.window(window_handles[-1])
            
            # Email
            self.logger.info("Inputting Email...")
            email_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']"))
            )
            email_input.send_keys(self.email)
            
            # Next
            self.driver.find_element(By.ID, "identifierNext").click()
            time.sleep(2)
            
            # Password
            self.logger.info("Inputting Password...")
            pass_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']"))
            )
            pass_input.send_keys(self.password)
            
            # Next to Finish
            self.driver.find_element(By.ID, "passwordNext").click()
            
            self.logger.info("Credentials submitted. Waiting for redirect...")
            time.sleep(5)
            
            # Switch back to main
            self.driver.switch_to.window(window_handles[0])
            time.sleep(5)
            self.logger.info("Login flow completed (Assumed success).")

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            # We might proceed as guest or fail? Detailed logs help.
            # self.driver.save_screenshot("login_fail.png")
            raise e

    async def scrape(self) -> List[Dict]:
        self.setup_driver()
        results = []
        
        try:
            # Skip Login for now due to CAPTCHA blocking automated attempts.
            # self.login_google() 
            self.logger.info("Attempting public scrape without login (Login blocked by Captcha)...")
            
            for sub in self.subreddits:
                self.logger.info(f"Scraping r/{sub}...")
                url = f"https://www.reddit.com/r/{sub}/new/"
                self.driver.get(url)
                time.sleep(3)
                
                try:
                    # Check if we are blocked/redirected to login
                    if "login" in self.driver.current_url or "humanity" in self.driver.title.lower():
                        self.logger.warning(f"Blocked from r/{sub} (Redirected to login/captcha).")
                        continue
                except:
                    pass

                # Scroll to load more
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # Extract Posts (Shreddit DOM or Classic)
                posts = self.driver.find_elements(By.TAG_NAME, "shreddit-post")
                
                if not posts:
                    posts = self.driver.find_elements(By.CLASS_NAME, "Post")

                self.logger.info(f"Found {len(posts)} potential posts in r/{sub}")
                
                limit = 10
                count = 0
                for p in posts:
                    if count >= limit: break
                    try:
                        title = p.get_attribute("post-title")
                        content = p.get_attribute("selftext") or "" 
                        
                        # Timestamp
                        created_ts = p.get_attribute("created-timestamp")
                        # url
                        permalink = p.get_attribute("permalink")
                        full_link = f"https://www.reddit.com{permalink}"

                        if title:
                            res = {
                                "title": title,
                                "content": content, 
                                "subreddit": sub,
                                "url": full_link,
                                "created_at": created_ts, 
                                "scraped_date": datetime.utcnow().isoformat(),
                                "source_entity": "Reddit"
                            }
                            results.append(res)
                            count += 1
                    except Exception as inner_e:
                        continue
                        
        except Exception as e:
            self.logger.error(f"Critical Scraping Error: {e}")
            if self.driver:
                self.driver.save_screenshot("scraper_crash.png")

        finally:
            if self.driver:
                self.driver.quit()
        
        self.logger.info(f"Scrape collected {len(results)} items.")
        return results

if __name__ == "__main__":
    # Test Run
    import asyncio
    scraper = RedditScraper()
    data = asyncio.run(scraper.scrape())
    print(json.dumps(data, indent=2))
