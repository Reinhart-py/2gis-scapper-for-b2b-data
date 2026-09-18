import random
import time
from urllib.parse import quote
from typing import Dict, Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


class GoogleMapsEngine:
    def __init__(self, headless: bool = False):
        self.driver = self._init_driver(headless)

    def _init_driver(self, headless: bool) -> webdriver.Chrome:
        opts = Options()
        if headless:
            opts.add_argument("--headless=new")
        
        # Standard desktop view flags
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--start-maximized")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        # Selenium 4.15+ has automatic driver management built-in
        service = Service()
        driver = webdriver.Chrome(service=service, options=opts)
        return driver

    def human_delay(self, a: float = 1.0, b: float = 2.0) -> None:
        time.sleep(random.uniform(a, b))

    def search_query(self, query_or_url: str) -> bool:
        if query_or_url.startswith("http://") or query_or_url.startswith("https://"):
            url = query_or_url
        else:
            encoded = quote(query_or_url.strip())
            url = f"https://www.google.com/maps/search/{encoded}?hl=en"

        self.driver.get(url)
        self.human_delay(3.0, 4.0)

        # Dismiss cookies / GDPR consent dialog if present
        try:
            for btn_xpath in [
                "//button[contains(@aria-label, 'Accept')]",
                "//button[contains(., 'Accept all')]",
                "//form//button"
            ]:
                btns = self.driver.find_elements(By.XPATH, btn_xpath)
                if btns:
                    btns[0].click()
                    self.human_delay(1.0, 1.5)
                    break
        except Exception:
            pass

        return True

    def scroll_results_pane(self) -> None:
        try:
            feed = self.driver.find_element(
                By.XPATH, 
                "//div[@role='feed'] | //div[contains(@aria-label, 'Results for')]"
            )
            scroll_amt = random.randint(600, 1000)
            self.driver.execute_script("arguments[0].scrollTop += arguments[1];", feed, scroll_amt)
            self.human_delay(1.5, 2.5)
        except Exception:
            self.driver.execute_script(f"window.scrollBy(0, {random.randint(500, 800)});")
            self.human_delay(1.2, 2.0)

    def extract_visible_cards(self) -> List:
        return self.driver.find_elements(
            By.XPATH, 
            "//div[@role='feed']//a[contains(@href, '/maps/place/')] | //a[contains(@href, '/maps/place/')]"
        )

    def parse_card_details(self, card) -> Optional[Dict[str, str]]:
        try:
            link = card.get_attribute("href")
            if not link:
                return None

            title = card.get_attribute("aria-label")
            if not title:
                title = card.text.split("\n")[0] if card.text else "null"

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
            self.human_delay(0.2, 0.4)
            card.click()
            self.human_delay(2.0, 3.0)

            data = {
                "link": link,
                "title": title.strip(),
                "category": "null",
                "phone": "null",
                "website": "null",
                "address": "null",
                "rating": "null",
                "reviews": "null",
            }

            try:
                phone_btn = self.driver.find_element(
                    By.XPATH, 
                    "//button[starts-with(@data-item-id, 'phone:')] | //button[contains(@aria-label, 'Phone')]"
                )
                data["phone"] = phone_btn.text.replace("Phone:", "").strip()
            except Exception:
                pass

            try:
                addr_btn = self.driver.find_element(
                    By.XPATH, 
                    "//button[@data-item-id='address'] | //button[contains(@aria-label, 'Address')]"
                )
                data["address"] = addr_btn.text.replace("Address:", "").strip()
            except Exception:
                pass

            try:
                web_btn = self.driver.find_element(
                    By.XPATH, 
                    "//a[@data-item-id='authority'] | //a[contains(@aria-label, 'Website')]"
                )
                data["website"] = web_btn.get_attribute("href")
            except Exception:
                pass

            try:
                stars_el = self.driver.find_element(
                    By.XPATH, 
                    "//div[contains(@class, 'F7nice')]//span[@aria-hidden='true']"
                )
                data["rating"] = stars_el.text.strip()
                revs_el = self.driver.find_element(
                    By.XPATH, 
                    "//div[contains(@class, 'F7nice')]//span[contains(@aria-label, 'reviews')]"
                )
                data["reviews"] = "".join(filter(str.isdigit, revs_el.text))
            except Exception:
                pass

            try:
                cat_btn = self.driver.find_element(
                    By.XPATH, 
                    "//button[contains(@jsaction, 'pane.rating.category')]"
                )
                data["category"] = cat_btn.text.strip()
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
