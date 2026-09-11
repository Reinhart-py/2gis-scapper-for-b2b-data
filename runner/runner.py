import time
from argparse import Namespace
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from executor import XPATHS, clean_dom_memory, create_session, find, navigate, quit_session
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

    def advance_to_page(self, driver, target_page: int) -> int:
        """Fast-forwards via the UI to reach the resume page if target_page > 1."""
        current = 1
        print(f"[*] Fast-forwarding to page {target_page}...")

        while current < target_page:
            # 1. Try clicking direct numbered button if visible in pagination
            try:
                target_btn = driver.find_elements(
                    By.XPATH,
                    f"//div[contains(@class, 'pagination')]//span[text()='{target_page}'] | //div[contains(@class, '_5ocwns')]//span[text()='{target_page}']",
                )
                if target_btn:
                    driver.execute_script("arguments[0].click();", target_btn[0])
                    time.sleep(2.5)
                    print(f"[+] Jumped directly to page {target_page} via pagination bar.")
                    return target_page
            except Exception:
                pass

            # 2. Otherwise advance page by page
            try:
                next_btn = find(driver, XPATHS["next_page_btn"])
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(0.15)
                driver.execute_script("arguments[0].click();", next_btn)
                current += 1
                time.sleep(1.2)
                if current % 5 == 0 or current == target_page:
                    print(f"    Navigated to page {current}/{target_page}...")
            except Exception as e:
                print(f"[!] Reached end of pagination or could not advance: {e}")
                break

        return current

    def run(self) -> None:
        write_csv_headers(self.output_dir)

        driver = create_session()
        driver.implicitly_wait(0)

        initial_url = build_search_query(
            city_name=self.city_name,
            query=self.query_string,
            country_tld=self.country_code,
        )
        print(f"\n[Init] Opening 2GIS: {initial_url}")
        navigate(driver=driver, url=initial_url)
        time.sleep(4.5)

        # Detect total pages
        num_of_pages = 1000
        try:
            page_count_element = find(driver, XPATHS["result_count"])
            raw_count = "".join(filter(str.isdigit, page_count_element.text))
            if raw_count:
                num_of_pages = (int(raw_count) // 12) + 2
            print(f"[Init] Total detected pages: ~{num_of_pages}")
        except Exception:
            print("[Init] Could not detect page count. Defaulting to 1000.")

        current_page = 1
        total_saved = self.initial_saved

        # If user requested to start/resume from page > 1, fast forward
        if self.start_page > 1:
            current_page = self.advance_to_page(driver, self.start_page)

        try:
            while current_page <= num_of_pages:
                print(f"\n>>> SCRAPING PAGE {current_page} | Total Collected: {total_saved} <<<")

                # Locate scroll container
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

                # Pre-scroll down to render virtualized cards
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
                    print(f"[*] No listings found on page {current_page}. Reached end of results.")
                    break

                print(f"Found {len(cards)} listings on page {current_page}")

                for card_idx, card in enumerate(cards, 1):
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

                        # Click card to open drawer
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
                        print(f"[{total_saved}] {title[:20]} | {p1} | {website}")

                        # Press ESC to close profile drawer & unmount sub-components
                        try:
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        except Exception:
                            pass

                    except Exception:
                        continue

                # Clean garbage and memory cache at the end of each page
                clean_dom_memory(driver)

                # Save checkpoint state
                save_state(
                    city=self.city_name,
                    query=self.query_string,
                    country=self.country_code,
                    page=current_page,
                    total_saved=total_saved,
                    output_path=self.output_dir,
                )

                # Advance to next page via UI button
                try:
                    next_btn = find(driver, XPATHS["next_page_btn"])
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", next_btn)
                    current_page += 1
                    time.sleep(2.5)
                except Exception as e:
                    print(f"[*] Could not find next page button or pagination ended: {e}")
                    break

        except KeyboardInterrupt:
            print("\n[!] Scraper stopped by user. Progress saved.")
        except Exception as err:
            print(f"\n[!] Unexpected error: {err}")
        finally:
            print(f"\n[✓] Finished. Total saved: {total_saved}")
            quit_session(driver)
            if current_page >= num_of_pages:
                clear_state()
