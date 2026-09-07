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

                # Find the scrollable container for the listings
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

                # Scroll down in increments to force 2GIS to lazy-load all 12 cards
                for _ in range(5):
                    if scroll_container:
                        driver.execute_script(
                            "arguments[0].scrollTop += 700;", scroll_container
                        )
                    else:
                        driver.execute_script("window.scrollBy(0, 700);")
                    time.sleep(0.3)

                # Fetch all cards now that DOM virtual items have mounted
                cards = driver.find_elements(
                    By.XPATH,
                    "//div[@class='_1kf6gff'] | //div[contains(@class, '_1469e3a')]",
                )
                if not cards:
                    cards = driver.find_elements(
                        By.XPATH, "//a[contains(@href, '/firm/')]"
                    )

                print(f"Found {len(cards)} listings on page {page}")

                for idx, card in enumerate(cards, 1):
                    try:
                        # Scroll the individual card into view
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});", card
                        )
                        time.sleep(0.1)

                        card_lines = [
                            line.strip()
                            for line in card.text.split("\n")
                            if line.strip()
                        ]
                        if not card_lines:
                            continue

                        title = card_lines[0]
                        address = (
                            card_lines[2]
                            if len(card_lines) > 2
                            else (card_lines[1] if len(card_lines) > 1 else "null")
                        )

                        # Open drawer
                        driver.execute_script("arguments[0].click();", card)
                        time.sleep(0.35)

                        # Unmask phone digits
                        try:
                            btns = driver.find_elements(
                                By.XPATH,
                                "//span[contains(text(), 'Show phone')] | //button[contains(., 'phone') or contains(., 'Phone')]",
                            )
                            if btns:
                                driver.execute_script(
                                    "arguments[0].click();", btns[0]
                                )
                                time.sleep(0.15)
                        except Exception:
                            pass

                        # Read revealed numbers
                        found_phones = []
                        tel_anchors = driver.find_elements(
                            By.XPATH, "//a[starts-with(@href, 'tel:')]"
                        )
                        for a in tel_anchors:
                            href_val = a.get_attribute("href")
                            if href_val:
                                num = href_val.replace("tel:", "").strip()
                                if num and num not in found_phones:
                                    found_phones.append(num)

                        found_phones.sort(
                            key=lambda x: 0 if ("971" in x) else 1
                        )

                        p1 = found_phones[0] if len(found_phones) > 0 else "null"
                        p2 = found_phones[1] if len(found_phones) > 1 else "null"
                        p3 = found_phones[2] if len(found_phones) > 2 else "null"

                        append_single_row(
                            self.output_dir, [title, p1, p2, p3, address]
                        )
                        total_saved += 1
                        print(f"[{total_saved}] {title[:28]} | {p1} | {p2} | {p3}")

                    except Exception:
                        continue

                # Scroll to bottom and click pagination button
                try:
                    next_btn = find(driver, XPATHS["next_page_btn"])
                    driver.execute_script(
                        "arguments[0].scrollIntoView(true);", next_btn
                    )
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
