import csv
import os
import time
from typing import List
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from .scraper import GoogleMapsEngine
from utils.state_manager import update_latest_progress

console = Console()
HEADERS = ["keyword", "title", "category", "primary_mobile", "secondary_phone", "website", "address", "rating", "reviews"]


class GMapsRunner:
    def __init__(self, target_input: str, output_path: str, start_index: int = 0, target_count: int = 0):
        self.target_input = target_input.strip('\'" \t\r\n')
        self.output_path = output_path.strip('\'" \t\r\n')
        self.current_idx = start_index
        self.target_count = target_count
        self.total_saved = 0

    def _load_keywords(self) -> List[str]:
        raw_path = os.path.abspath(os.path.expanduser(self.target_input))
        if os.path.isfile(raw_path):
            ext = os.path.splitext(raw_path)[1].lower()
            try:
                if ext in [".xlsx", ".xls"]:
                    df = pd.read_excel(raw_path)
                elif ext == ".csv":
                    df = pd.read_csv(raw_path)
                else:
                    with open(raw_path, "r", encoding="utf-8") as f:
                        return [line.strip() for line in f if line.strip()]

                if df.shape[1] > 1:
                    return df.apply(lambda row: " ".join(row.dropna().astype(str)), axis=1).tolist()
                else:
                    return [str(val).strip() for val in df.iloc[:, 0].dropna().tolist()]
            except Exception as e:
                console.print(f"[bold red]✖ Error parsing file:[/bold red] {e}")
                return [self.target_input]

        return [self.target_input]

    def _init_csv(self) -> None:
        abs_output = os.path.abspath(os.path.expanduser(self.output_path))
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)
        if not os.path.exists(abs_output) or os.path.getsize(abs_output) == 0:
            with open(abs_output, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)

    def run(self) -> None:
        self._init_csv()
        keywords = self._load_keywords()

        console.print(
            Panel(
                f"[bold cyan]TARGET SOURCE:[/bold cyan] [white]{self.target_input}[/white]\n"
                f"[bold cyan]QUEUED TASKS:[/bold cyan]  [bold yellow]{len(keywords)} items[/bold yellow]\n"
                f"[bold cyan]EXPORT DEST:[/bold cyan]    [dim]{self.output_path}[/dim]",
                title="[bold #00f0ff]◈ GOOGLE MAPS EXTRACTION CLUSTER ◈[/bold #00f0ff]",
                border_style="cyan",
                padding=(0, 2)
            )
        )

        engine = GoogleMapsEngine(headless=False)

        try:
            for idx in range(self.current_idx, len(keywords)):
                kw = keywords[idx]
                target_str = f"/{self.target_count}" if self.target_count > 0 else ""
                
                console.print(f"\n[bold black on #00f0ff] ❖ [{idx+1}/{len(keywords)}] TASK: {kw.upper()} ❖ [/bold black on #00f0ff]")

                # Execute search with 20s loading sentry
                with console.status(f"[bold yellow]Connecting & awaiting Google response (Max 20s sentry)...", spinner="bouncingBar"):
                    is_loaded = engine.search_query(kw)

                if not is_loaded:
                    console.print(f"[bold red]⚠ Sentry Alert:[/bold red] Network stalled or no response after 20s for '{kw}'. Skipping to next task.")
                    update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)
                    continue

                seen_links = set()
                stagnant_scroll_count = 0
                max_scrolls = 25

                # Check if query resolved directly into a place card
                if engine.is_single_place_view():
                    console.print("[dim cyan]↳ Single company entity resolved directly[/dim cyan]")
                    details = engine.parse_active_place_pane()
                    if details and details["title"] != "null":
                        row = [
                            kw, details["title"], details["category"], details["phone_1"],
                            details["phone_2"], details["website"], details["address"],
                            details["rating"], details["reviews"]
                        ]
                        with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                            csv.writer(f).writerow(row)
                        self.total_saved += 1
                        console.print(f" [bold #00ff66]✔ #{self.total_saved}[/bold #00ff66] [white bold]{details['title'][:25]}[/white bold] | [yellow]{details['phone_1']}[/yellow] | [dim blue]{details['website'][:24]}[/dim blue]")

                    update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)
                    continue

                for _ in range(max_scrolls):
                    if self.target_count > 0 and self.total_saved >= self.target_count:
                        break

                    cards = engine.extract_visible_cards()
                    new_cards_found = 0

                    for card in cards:
                        if self.target_count > 0 and self.total_saved >= self.target_count:
                            break

                        try:
                            href = card.get_attribute("href")
                            if not href or href in seen_links:
                                continue

                            details = engine.parse_card_details(card)
                            if details and details.get("link"):
                                seen_links.add(details["link"])
                                row = [
                                    kw, details["title"], details["category"], details["phone_1"],
                                    details["phone_2"], details["website"], details["address"],
                                    details["rating"], details["reviews"]
                                ]
                                with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                                    csv.writer(f).writerow(row)

                                self.total_saved += 1
                                new_cards_found += 1
                                
                                # High priority badge if private/mobile number detected
                                mob_badge = "[bold green]📱 MOBILE[/bold green]" if ("+9715" in details["phone_1"] or "+91" in details["phone_1"]) else "[dim]☎ LINE[/dim]"
                                console.print(f" [bold #00f0ff]#{self.total_saved:<5}[/bold #00f0ff] [white]{details['title'][:24]:<24}[/white] | {mob_badge} [yellow]{details['phone_1']:<16}[/yellow] | [dim]{details['website'][:22]}[/dim]")
                        except Exception:
                            continue

                    # Termination checks
                    if engine.is_end_of_list():
                        console.print("[dim cyan]↳ End of directory reached for this search term.[/dim cyan]")
                        break

                    has_moved, _ = engine.scroll_results_pane()
                    if new_cards_found == 0 and not has_moved:
                        stagnant_scroll_count += 1
                    else:
                        stagnant_scroll_count = 0

                    if stagnant_scroll_count >= 2:
                        console.print("[dim cyan]↳ Directory scroll threshold satisfied. Proceeding...[/dim cyan]")
                        break

                update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)

                if self.target_count > 0 and self.total_saved >= self.target_count:
                    console.print(f"\n[bold #00ff66]✔ Target lead threshold of {self.target_count} successfully collected![/bold #00ff66]")
                    break

        except KeyboardInterrupt:
            console.print("\n[bold yellow]! Pipeline paused by user. Checkpoints preserved.[/bold yellow]")
        finally:
            engine.close()
