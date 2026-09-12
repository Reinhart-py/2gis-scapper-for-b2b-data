import time
from argparse import Namespace

from rich.console import Console
from rich.table import Table
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from executor import XPATHS, clean_dom_memory, create_session, find, navigate, quit_session
from io_handler.handler import append_single_row, write_csv_headers
from utils import build_search_query, clear_state, save_state

console = Console()


class Runner:
    def __init__(self, config: Namespace) -> None:
        self.country_code: str = getattr(config, "country", "ae")
        self.city_name: str = config.city_name
        self.query_string: str = config.query_string
        self.output_dir: str = config.output_path
        self.start_page: int = getattr(config, "start_page", 1)
        self.initial_saved: int = getattr(config, "initial_saved", 0)
        self.target_count: int = getattr(config, "target_count", 0)

    def advance_to_page(self, driver, target_page: int) -> int:
        current = 1
        console.print(f"[bold cyan]⚡ Fast-forwarding directly to Page {target_page}...[/bold cyan]")
        
        with console.status("[bold yellow]Skipping earlier pages without extracting...", spinner="dots"):
            while current < target_page:
                try:
                    target_btn = driver.find_elements(
                        By.XPATH,
                        f"//div[contains(@class, 'pagination')]//span[text()='{target_page}'] | //div[contains(@class, '_5ocwns')]//span[text()='{target_page}']",
                    )
                    if target_btn:
                        driver.execute_script("arguments[0].click();", target_btn[0])
                        time.sleep(2.0)
                        return target_page
                except Exception:
                    pass

                try:
                    next_btn = find(driver, XPATHS["next_page_btn"])
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(0.1)
                    driver.execute_script("arguments[0].click();", next_btn)
                    current += 1
                    time.sleep(0.7)
                except Exception as e:
                    console.print(f"[red]! Fast-forward hit end of list at Page {current}: {e}[/red]")
                    break
        return current

    def run(self) -> None:
        write_csv_headers(self.output_dir)
        current_page = self.start_page
        total_saved = self.initial_saved
        num_of_pages = 1000

        # Outer resilience loop: restores session automatically if browser process dies
        while True:
            if self.target_count > 0 and total_saved >= self.target_count:
                console.print(f"\n[bold green]✔ Target of {self.target_count} leads successfully harvested![/bold green]")
                clear_state()
                break

            driver = None
            try:
                driver = create_session()
                driver.implicitly_wait(0)

                initial_url = build_search_query(
                    city_name=self.city_name,
                    query=self.query_string,
                    country_tld=self.country_code,
                )
                navigate(driver=driver, url=initial_url)
                time.sleep(4.0)

                if current_page == 1:
                    try:
                        page_count_el = find(driver, XPATHS["result_count"])
                        raw_c = "".join(filter(str.isdigit, page_count_el.text))
                        if raw_c:
                            num_of_pages = (int(raw_c) // 12) + 2
                        console.print(f"[dim cyan]ℹ Detected ~{num_of_pages} available catalog pages[/dim cyan]")
                    except Exception:
                        pass

                if current_page > 1:
                    current_page = self.advance_to_page(driver, current_page)

                while current_page <= num_of_pages:
                    if self.target_count > 0 and total_saved >= self.target_count:
                        break

                    target_str = f"/{self.target_count}" if self.target_count > 0 else ""
                    console.print(f"\n[bold white on #1a1a24] ◈ PAGE {current_page} ◈ | Extracted: [bold #39ff14]{total_saved}{target_str}[/bold #39ff14] [/bold white on #1a1a24]")

                    scroll_container = None
                    for xpath in [
                        "(//div[@class='_15gu4wr'])[3]",
                        "(//div[@class='_15gu4wr'])[2]",
                        "//div[contains(@class, 'sidebar')]",
                    ]:
                        try:
                            scroll_container = driver.find_element(By.XPATH, xpath)
                            break
                        except Exception:
                            continue

                    for _ in range(5):
                        try:
                            if scroll_container:
                                driver.execute_script("arguments[0].scrollTop += 700;", scroll_container)
                            else:
                                driver.execute_script("window.scrollBy(0, 700);")
                            time.sleep(0.2)
                        except Exception:
                            break

                    cards = driver.find_elements(
                        By.XPATH,
                        "//div[@class='_1kf6gff'] | //div[contains(@class, '_1469e3a')]",
                    )
                    if not cards:
                        cards = driver.find_elements(By.XPATH, "//a[contains(@href, '/firm/')]")

                    if not cards:
                        console.print(f"[yellow]✦ No further cards detected on Page {current_page}. Reached catalog end.[/yellow]")
                        return

                    for card in cards:
                        if self.target_count > 0 and total_saved >= self.target_count:
                            break

                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                            time.sleep(0.05)

                            lines = [line.strip() for line in card.text.split("\n") if line.strip()]
                            if not lines:
                                continue

                            title = lines[0]
                            address = "null"
                            for line in lines[1:]:
                                if any(k in line.lower() for k in ["street", "road", "tower", "building", "floor", "bay", "dubai", "abu dhabi", "industrial"]):
                                    address = line
                                    break
                            if address == "null" and len(lines) > 2:
                                address = lines[2]

                            # Open firm drawer
                            driver.execute_script("arguments[0].click();", card)
                            time.sleep(0.3)

                            # Reveal hidden phone digits
                            try:
                                btns = driver.find_elements(
                                    By.XPATH,
                                    "//span[contains(text(), 'Show phone')] | //button[contains(., 'phone') or contains(., 'Phone')]",
                                )
                                if btns:
                                    driver.execute_script("arguments[0].click();", btns[0])
                                    time.sleep(0.1)
                            except Exception:
                                pass

                            found_phones = []
                            for a in driver.find_elements(By.XPATH, "//a[starts-with(@href, 'tel:')]"):
                                h = a.get_attribute("href")
                                if h:
                                    num = h.replace("tel:", "").strip()
                                    if num and num not in found_phones:
                                        found_phones.append(num)

                            found_phones.sort(key=lambda x: 0 if ("971" in x) else 1)
                            p1 = found_phones[0] if len(found_phones) > 0 else "null"
                            p2 = found_phones[1] if len(found_phones) > 1 else "null"
                            p3 = found_phones[2] if len(found_phones) > 2 else "null"

                            website = "null"
                            for w in driver.find_elements(
                                By.XPATH,
                                "//a[contains(@href, 'http') and not(contains(@href, '2gis')) and not(contains(@href, 'google')) and not(starts-with(@href, 'tel:'))]",
                            ):
                                raw_h = w.get_attribute("href")
                                txt = w.text.strip()
                                if raw_h and ("." in txt or "http" in raw_h):
                                    website = txt if "." in txt else raw_h
                                    break

                            category = "null"
                            try:
                                info_tab = driver.find_elements(
                                    By.XPATH,
                                    "//div[text()='Info'] | //button[contains(., 'Info')] | //a[contains(@href, '/tab/info')]",
                                )
                                if info_tab:
                                    driver.execute_script("arguments[0].click();", info_tab[0])
                                    time.sleep(0.2)
                                    cat_nodes = driver.find_elements(
                                        By.XPATH,
                                        "//div[contains(text(), 'Categories')]/following-sibling::div//a | //div[contains(text(), 'Categories')]/..//a",
                                    )
                                    cat_names = [c.text.strip() for c in cat_nodes if c.text.strip()]
                                    if cat_names:
                                        category = " | ".join(cat_names)
                            except Exception:
                                pass

                            if category == "null" and len(lines) > 1 and "street" not in lines[1].lower():
                                category = lines[1]

                            append_single_row(self.output_dir, [title, category, p1, p2, p3, website, address])
                            total_saved += 1
                            console.print(f" [bold cyan]#{total_saved:<5}[/bold cyan] [white]{title[:24]:<24}[/white] | [yellow]{p1:<16}[/yellow] | [dim blue]{website[:28]}[/dim blue]")

                            try:
                                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                            except Exception:
                                pass

                        except Exception:
                            continue

                    clean_dom_memory(driver)
                    save_state(
                        city=self.city_name,
                        query=self.query_string,
                        country=self.country_code,
                        page=current_page,
                        total_saved=total_saved,
                        output_path=self.output_dir,
                        target_count=self.target_count,
                    )

                    next_btn = find(driver, XPATHS["next_page_btn"])
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", next_btn)
                    current_page += 1
                    time.sleep(2.0)

            except KeyboardInterrupt:
                console.print("\n[bold yellow]! Scraper interrupted by user. Progress safely secured.[/bold yellow]")
                break
            except Exception as crash_err:
                console.print(f"\n[bold red]! Browser memory overflow / crash intercepted at Page {current_page}: {crash_err}[/bold red]")
                console.print("[bold cyan]⟳ Reviving Chromium session and picking up from exact page in 3s...[/bold cyan]")
                time.sleep(3)
            finally:
                quit_session(driver)

            if current_page > num_of_pages:
                console.print("\n[bold green]✔ All available pages scraped.[/bold green]")
                clear_state()
                break
