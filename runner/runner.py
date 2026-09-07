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

                # Locate the left scrollable sidebar
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

                # Scroll down in short increments to mount all 12 cards in DOM
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

                        # Detect address from card preview
                        address = "null"
                        for line in card_lines[1:]:
                            if any(k in line.lower() for k in ["street", "road", "tower", "building", "floor", "bay", "dubai", "industrial"]):
                                address = line
                                break
                        if address == "null" and len(card_lines) > 2:
                            address = card_lines[2]

                        # Open business profile drawer (defaults to Contacts tab)
                        driver.execute_script("arguments[0].click();", card)
                        time.sleep(0.4)

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

                        # Switch to 'Info' tab to get detailed categories
                        category = "null"
                        try:
                            info_tab = driver.find_elements(
                                By.XPATH,
                                "//div[text()='Info'] | //button[contains(., 'Info')] | //a[contains(@href, '/tab/info')]"
                            )
                            if info_tab:
                                driver.execute_script("arguments[0].click();", info_tab[0])
                                time.sleep(0.25)

                                # Match items inside the Categories section
                                cat_nodes = driver.find_elements(
                                    By.XPATH,
                                    "//div[contains(text(), 'Categories')]/following-sibling::div//a | //div[contains(text(), 'Categories')]/..//a"
                                )
                                cat_names = [c.text.strip() for c in cat_nodes if c.text.strip()]
                                if cat_names:
                                    category = " | ".join(cat_names)
                        except Exception:
                            pass

                        # Fallback to card category text if Info tab has no entries
                        if category == "null":
                            if len(card_lines) > 1 and "street" not in card_lines[1].lower():
                                category = card_lines[1]

                        append_single_row(
                            self.output_dir, [title, category, p1, p2, p3, website, address]
                        )
                        total_saved += 1
                        print(f"[{total_saved}] {title[:20]} | Cat: {category[:25]} | {p1} | {website}")

                    except Exception:
                        continue

                # Advance to next page
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
