import time
from argparse import Namespace
from selenium.webdriver.common.by import By
from executor import XPATHS, create_session, find, navigate, quit_session
from io_handler.handler import write_csv_headers, append_single_row
from utils import build_search_query


class Runner:
    def __init__(self, config: Namespace) -> None:
        country_code = getattr(config, "country", "ae")
        self.search_query: str = build_search_query(
            city_name=config.city_name,
            query=config.query_string,
            country_tld=country_code,
        )
        self.output_dir: str = config.output_path

    def run(self) -> None:
        write_csv_headers(self.output_dir)

        driver = create_session()
        driver.implicitly_wait(0)

        print(f"Opening 2GIS: {self.search_query}")
        navigate(driver=driver, url=self.search_query)
        time.sleep(4)

        try:
            page_count_element = find(driver, XPATHS["result_count"])
            num_of_pages = (int(page_count_element.text) // 12) + 3
        except Exception:
            num_of_pages = 50

        print(f"Total detected pages: {num_of_pages - 2}")
        total_saved = 0

        try:
            for page in range(1, num_of_pages):
                print(f"\n>>> SCRAPING PAGE {page} <<<")

                # Locate scrollable listing panel
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

                # Scroll to force lazy-loading of all 12 items
                for _ in range(5):
                    if scroll_container:
                        driver.execute_script("arguments[0].scrollTop += 700;", scroll_container)
                    else:
                        driver.execute_script("window.scrollBy(0, 700);")
                    time.sleep(0.3)

                cards = driver.find_elements(
                    By.XPATH,
                    "//div[@class='_1kf6gff'] | //div[contains(@class, '_1469e3a')]",
                )
                if not cards:
                    cards = driver.find_elements(By.XPATH, "//a[contains(@href, '/firm/')]")

                print(f"Found {len(cards)} listings on page {page}")

                for idx, card in enumerate(cards, 1):
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

                        # Category: line 1 or sub-badge if available
                        category = "null"
                        if len(card_lines) > 1:
                            category = card_lines[1]
                        if len(card_lines) > 3 and "street" not in card_lines[-1].lower() and "tower" not in card_lines[-1].lower():
                            # If bottom line has specific niche like 'Manufacturing Process Automation'
                            category = f"{category} | {card_lines[-1]}"

                        # Address: typically line 2 or 3
                        address = "null"
                        for line in card_lines[1:]:
                            if any(k in line.lower() for k in ["street", "road", "tower", "building", "floor", "bay", "dubai", "industrial"]):
                                address = line
                                break
                        if address == "null" and len(card_lines) > 2:
                            address = card_lines[2]

                        # Click card to open drawer
                        driver.execute_script("arguments[0].click();", card)
                        time.sleep(0.35)

                        # Click show phone button
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

                        # Phone Numbers
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

                        # Website extraction (external URL anchors inside drawer)
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

                        append_single_row(
                            self.output_dir, [title, category, p1, p2, p3, website, address]
                        )
                        total_saved += 1
                        print(f"[{total_saved}] {title[:22]} | {category[:15]} | {p1} | {website}")

                    except Exception:
                        continue

                # Go to next page
                try:
                    next_btn = find(driver, XPATHS["next_page_btn"])
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(0.4)
                    driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(2.5)
                except Exception:
                    print("End of search results or pagination ended.")
                    break

        finally:
            print(f"\nFinished! Total businesses saved: {total_saved}")
            time.sleep(1)
            quit_session(driver)
