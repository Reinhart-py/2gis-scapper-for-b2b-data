import random
import time
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager


class GoogleMapsEngine:
    def __init__(self, headless: bool = True):
        self.driver = self._init_driver(headless)

    def _init_driver(self, headless: bool) -> webdriver.Chrome:
        opts = webdriver.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        return driver

    def human_delay(self, a: float = 1.0, b: float = 2.5) -> None:
        time.sleep(random.uniform(a, b))

    def search_query(self, query_or_url: str) -> bool:
        if query_or_url.startswith("http://") or query_or_url.startswith("https://"):
            self.driver.get(query_or_url)
        else:
            self.driver.get("https://www.google.com/maps?hl=en")
            self.human_delay(1.5, 2.8)
            try:
                # Bypass consent popups if present
                for btn_xpath in ["//button[contains(@aria-label, 'Accept')]", "//button[contains(., 'Accept all')]"]:
                    btns = self.driver.find_elements(By.XPATH, btn_xpath)
                    if btns:
                        btns[0].click()
                        break
            except Exception:
                pass

            try:
                search_box = self.driver.find_element(By.ID, "searchboxinput")
                search_box.click()
                search_box.clear()
                for char in query_or_url:
                    search_box.send_keys(char)
                    time.sleep(random.uniform(0.04, 0.12))
                self.human_delay(0.4, 0.8)
                search_box.send_keys(Keys.ENTER)
            except Exception:
                return False

        self.human_delay(3.0, 4.5)
        return True

    def scroll_results_pane(self) -> None:
        try:
            feed = self.driver.find_element(By.XPATH, "//div[@role='feed']")
            # Variable jitter scrolling to prevent automated rate limiting
            scroll_amount = random.randint(500, 900)
            self.driver.execute_script("arguments[0].scrollTop += arguments[1];", feed, scroll_amount)
            self.human_delay(1.2, 2.2)
        except Exception:
            self.driver.execute_script(f"window.scrollBy(0, {random.randint(400, 700)});")
            self.human_delay(1.0, 1.8)

    def extract_visible_cards(self) -> list:
        return self.driver.find_elements(By.XPATH, "//div[contains(@class, 'Nv2PK')]")

    def parse_card_details(self, card) -> Optional[Dict[str, str]]:
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
            self.human_delay(0.2, 0.5)
            
            # Click card to load pane
            card.click()
            self.human_delay(1.8, 2.6)

            data = {
                "title": "null",
                "category": "null",
                "phone": "null",
                "website": "null",
                "address": "null",
                "rating": "null",
                "reviews": "null",
            }

            try:
                data["title"] = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'DUwDvf')]").text.strip()
            except Exception:
                pass

            try:
                data["category"] = self.driver.find_element(By.XPATH, "//button[contains(@jsaction, 'pane.rating.category')]").text.strip()
            except Exception:
                pass

            try:
                data["address"] = self.driver.find_element(By.XPATH, "//button[@data-item-id='address']//div[contains(@class, 'fontBodyMedium')]").text.strip()
            except Exception:
                pass

            try:
                data["phone"] = self.driver.find_element(By.XPATH, "//button[starts-with(@data-item-id, 'phone:')]//div[contains(@class, 'fontBodyMedium')]").text.strip()
            except Exception:
                pass

            try:
                web_elem = self.driver.find_element(By.XPATH, "//a[@data-item-id='authority']")
                data["website"] = web_elem.get_attribute("href")
            except Exception:
                pass

            try:
                stars_el = self.driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]//span[@aria-hidden='true']")
                data["rating"] = stars_el.text.strip()
                revs_el = self.driver.find_element(By.XPATH, "//div[contains(@class, 'F7nice')]//span[contains(@aria-label, 'reviews')]")
                data["reviews"] = "".join(filter(str.isdigit, revs_el.text))
            except Exception:
                pass

            return data
        except Exception:
            return None

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass
