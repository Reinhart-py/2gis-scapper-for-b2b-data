import time
from argparse import Namespace
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from executor import XPATHS, create_session, find, navigate, quit_session
from io_handler.handler import write_csv_headers, append_single_row
from utils import build_search_query, save_state, clear_state


class Runner:
    def __init__(self, config: Namespace) -> None:
        self.country_code: str = getattr(config, "country", "ae")
        self.city_name: str = config.city_name
        self.query_string: str = config.query_string
        self.output_dir: str = config.output_path
        self.start_page: int = getattr(config, "start_page", 1)
        self.initial_saved: int = getattr(config, "initial_saved", 0)
        self.recycle_every_pages: int = 25  # Chrome recycle threshold

    def get_url(self, page: int = 1) -> str:
        return build_search_query(
            city_name=self.city_name,
            query=self.query_string,
            country_tld=self.country_code,
            page=page,
        )

    def run(self) -> None:
        write_csv_headers(self.output_dir)

        driver = None
        current_page = self.start_page
        num_of_pages = current_page + 50
        total_saved = self.initial_saved

        # Bootstrap session to inspect total pages if starting from page 1
        if self.start_page == 1:
            try:
                driver = create_session()
                driver.implicitly_wait(0)
                initial_url = self.get_url(1)
                print(f"[Init] Opening 2GIS: {initial_url}")
                navigate(driver=driver, url=initial_url)
                time.sleep(3.5)

                try:
                    page_count_element = find(driver, XPATHS["result_count"])
                    num_of_pages = (int(page_count_element.text.replace(" ", "")) // 12) + 3
                except Exception:
                    num_of_pages = 1000
                print(f"[Init] Total detected pages: ~{num_of_pages - 2}")
            except Exception as e:
                print(f"[!] Warning checking page count: {e}")
            finally:
                quit_session(driver)
                driver = None
        else:
            num_of_pages = 1000

        while current_page < num_of_pages:
            batch_end_page = min(current_page + self.recycle_every_pages, num_of_pages)
            print(f"\n[Lifecycle] Starting fresh Chrome process (Pages {current_page} to {batch_end_page - 1})...")

            try:
                driver = create_session()
                driver.implicitly_wait(0)

                target_url = self.get_url(current_page)
                navigate(driver=driver, url=target_url)
                time.sleep(3.5)

                while current_page < batch_end_page:
                    print(f"\n>>> SCRAPING PAGE {current_page} | Total Collected: {total_saved} <<<")

                    # Locate scrollable drawer
                    scroll_container = None
                    for container_xpath in [
                        "(//div[@class='_15gu4wr'])[3]",
                        "(//div[@class='_15gu4wr'])[2]",
                        "//div[contains(@class, 'sidebar')]",
                    ]:
                        try:
                            scroll_container = driver.find_element(By.XPATH, container_xpath)
                            break
                        except Exception:
                            continue

                    # Pre-scroll down to render lazy cards
                    for _ in range(5):
                        try:
                            if scroll_container:
                                driver.execute_script("arguments[0].scrollTop += 700;", scroll_container)
                            else:
                                driver.execute_script("window.scrollBy(0, 700);")
                            time.sleep(0.25)
                        except Exception:
                            break

                    cards = driver.find_elements(
                        By.XPATH,
                        "//div[@class='_1kf6gff'] | //div[contains(@class, '_1469e3a')]",
                    )
                    if not cards:
                        cards = driver.find_elements(By.XPATH, "//a[contains(@href, '/firm/')]")

                    if not cards:
                        print(f"[*] No listings found on page {current_page}. Reached the end.")
                        current_page = num_of_pages
                        break

                    print(f"Found {len(cards)} listings on page {current_page}")

                    for card in cards:
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                            time.sleep(0.1)

                            card_lines = [
                                line.strip()
                                for line in card.text.split("\n")
                                if line.strip()
                            ]
                            if not card_lines:
                                continue

                            title = card_lines[0]

                            address = "null"
                            for line in card_lines[1:]:
                                if any(k in line.lower() for k in ["street", "road", "tower", "building", "floor", "bay", "dubai", "abu dhabi", "industrial"]):
                                    address = line
                                    break
                            if address == "null" and len(card_lines) > 2:
                                address = card_lines[2]

                            # Open firm profile
                            driver.execute_script("arguments[0].click();", card)
                            time.sleep(0.35)

                            # Reveal hidden phone digits
                            try:
                                btns = driver.find_elements(
                                    By.XPATH,
                                    "//span[contains(text(), 'Show phone')] | //button[contains(., 'phone') or contains(., 'Phone')]",
                                )
                                if btns:
                                    driver.execute_script("arguments[0].click();", btns[0])
                                    time.sleep(0.15)
                            except Exception:
                                pass

                            # Extract phone numbers
                            found_phones = []
                            tel_anchors = driver.find_elements(By.XPATH, "//a[starts-with(@href, 'tel:')]")
                            for a in tel_anchors:
                                href_val = a.get_attribute("href")
                                if href_val:
                                    num = href_val.replace("tel:", "").strip()
                                    if num and num not in found_phones:
                                        found_phones.append(num)

                            found_phones.sort(key=lambda x: 0 if ("971" in x) else 1)
                            p1 = found_phones[0] if len(found_phones) > 0 else "null"
                            p2 = found_phones[1] if len(found_phones) > 1 else "null"
                            p3 = found_phones[2] if len(found_phones) > 2 else "null"

                            # Extract website URL
                            website = "null"
                            web_anchors = driver.find_elements(
                                By.XPATH,
                                "//a[contains(@href, 'http') and not(contains(@href, '2gis')) and not(contains(@href, 'google')) and not(starts-with(@href, 'tel:'))]"
                            )
                            for w in web_anchors:
                                raw_href = w.get_attribute("href")
                                text_val = w.text.strip()
                                if raw_href and ("." in text_val or "http" in raw_href):
                                    website = text_val if "." in text_val else raw_href
                                    break

                            # Categories from Info tab
                            category = "null"
                            try:
                                info_tab = driver.find_elements(
                                    By.XPATH,
                                    "//div[text()='Info'] | //button[contains(., 'Info')] | //a[contains(@href, '/tab/info')]"
                                )
                                if info_tab:
                                    driver.execute_script("arguments[0].click();", info_tab[0])
                                    time.sleep(0.25)

                                    cat_nodes = driver.find_elements(
                                        By.XPATH,
                                        "//div[contains(text(), 'Categories')]/following-sibling::div//a | //div[contains(text(), 'Categories')]/..//a"
                                    )
                                    cat_names = [c.text.strip() for c in cat_nodes if c.text.strip()]
                                    if cat_names:
                                        category = " | ".join(cat_names)
                            except Exception:
                                pass

                            if category == "null" and len(card_lines) > 1 and "street" not in card_lines[1].lower():
                                category = card_lines[1]

                            append_single_row(
                                self.output_dir, [title, category, p1, p2, p3, website, address]
                            )
                            total_saved += 1
                            print(f"[{total_saved}] {title[:22]} | {p1} | {website}")

                        except Exception:
                            continue

                    # Save state checkpoint after every successfully scraped page
                    save_state(
                        city=self.city_name,
                        query=self.query_string,
                        country=self.country_code,
                        page=current_page,
                        total_saved=total_saved,
                        output_path=self.output_dir,
                    )

                    current_page += 1

                    # Pagination transition
                    if current_page < batch_end_page:
                        try:
                            next_btn = find(driver, XPATHS["next_page_btn"])
                            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                            time.sleep(0.3)
                            driver.execute_script("arguments[0].click();", next_btn)
                            time.sleep(2.5)
                        except Exception:
                            driver.get(self.get_url(current_page))
                            time.sleep(3.0)

            except (WebDriverException, Exception) as crash_err:
                print(f"[!] Session interrupted at page {current_page}: {crash_err}")
                print("[!] Recycling browser session and resuming at current page...")
                time.sleep(2)
            finally:
                quit_session(driver)
                driver = None

        print(f"\n[✓] Job Finished! Total businesses saved: {total_saved}")
        clear_state()
