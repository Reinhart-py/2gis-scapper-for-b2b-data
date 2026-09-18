import random
import time
from urllib.parse import quote
from typing import Dict, Optional, List, Tuple
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
        
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--start-maximized")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)

        service = Service()
        driver = webdriver.Chrome(service=service, options=opts)
        return driver

    def human_delay(self, a: float = 0.8, b: float = 1.6) -> None:
        time.sleep(random.uniform(a, b))

    def search_query(self, query_or_url: str) -> bool:
        if query_or_url.startswith("http://") or query_or_url.startswith("https://"):
            url = query_or_url
        else:
            encoded = quote(query_or_url.strip())
            url = f"https://www.google.com/maps/search/{encoded}?hl=en"

        self.driver.get(url)
        self.human_delay(2.5, 3.5)

        # Handle consent
        try:
            for btn_xpath in [
                "//button[contains(@aria-label, 'Accept')]",
                "//button[contains(., 'Accept all')]",
                "//form//button"
            ]:
                btns = self.driver.find_elements(By.XPATH, btn_xpath)
                if btns:
                    btns[0].click()
                    self.human_delay(0.8, 1.2)
                    break
        except Exception:
            pass

        return True

    def is_end_of_list(self) -> bool:
        """Checks if Google Maps explicitly rendered 'You've reached the end of the list'."""
        try:
            end_markers = self.driver.find_elements(
                By.XPATH,
                "//span[contains(text(), \"You've reached the end of the list\")] | "
                "//div[contains(text(), \"You've reached the end of the list\")] | "
                "//span[contains(text(), 'No more results')] | "
                "//div[contains(@class, 'HlvSq')]"
            )
            return len(end_markers) > 0
        except Exception:
            return False

    def is_single_place_view(self) -> bool:
        """Checks if Google Maps redirected straight into a single business place pane."""
        return "/maps/place/" in self.driver.current_url

    def scroll_results_pane(self) -> Tuple[bool, int]:
        """Scrolls feed and returns (has_scrolled, current_scroll_height)."""
        try:
            feed = self.driver.find_element(
                By.XPATH, 
                "//div[@role='feed'] | //div[contains(@aria-label, 'Results for')]"
            )
            old_top = self.driver.execute_script("return arguments[0].scrollTop;", feed)
            scroll_amt = random.randint(700, 1100)
            self.driver.execute_script("arguments[0].scrollTop += arguments[1];", feed, scroll_amt)
            self.human_delay(1.2, 1.8)
            new_top = self.driver.execute_script("return arguments[0].scrollTop;", feed)
            return (new_top > old_top, new_top)
        except Exception:
            self.driver.execute_script(f"window.scrollBy(0, {random.randint(500, 800)});")
            self.human_delay(1.0, 1.5)
            return (True, 0)

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
            self.human_delay(0.1, 0.2)
            card.click()
            self.human_delay(1.5, 2.3)

            return self.parse_active_place_pane(link, title)
        except Exception:
            return None

    def parse_active_place_pane(self, link: str = "", title: str = "") -> Optional[Dict[str, str]]:
        """Extracts business data from the opened left info pane."""
        try:
            if not link:
                link = self.driver.current_url
            if not title:
                try:
                    title = self.driver.find_element(By.XPATH, "//h1[contains(@class, 'DUwDvf')]").text.strip()
                except Exception:
                    title = "null"

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
