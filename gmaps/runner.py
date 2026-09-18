import csv
import os
import time
from typing import List
import pandas as pd
from rich.console import Console
from .scraper import GoogleMapsEngine
from utils.state_manager import update_latest_progress

console = Console()
HEADERS = ["keyword", "title", "category", "phone", "website", "address", "rating", "reviews"]


class GMapsRunner:
    def __init__(self, target_input: str, output_path: str, start_index: int = 0, target_count: int = 0):
        self.target_input = target_input
        self.output_path = output_path
        self.current_idx = start_index
        self.target_count = target_count
        self.total_saved = 0

    def _load_keywords(self) -> List[str]:
        if os.path.isfile(self.target_input):
            ext = os.path.splitext(self.target_input)[1].lower()
            if ext in [".xlsx", ".xls"]:
                df = pd.read_excel(self.target_input)
            elif ext == ".csv":
                df = pd.read_csv(self.target_input)
            else:
                with open(self.target_input, "r", encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]

            # If the user created multiple columns in a table, combine them into one search query
            if df.shape[1] > 1:
                return df.apply(lambda row: " ".join(row.dropna().astype(str)), axis=1).tolist()
            else:
                return [str(val).strip() for val in df.iloc[:, 0].dropna().tolist()]

        return [self.target_input]

    def _init_csv(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.output_path)), exist_ok=True)
        if not os.path.exists(self.output_path) or os.path.getsize(self.output_path) == 0:
            with open(self.output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)

    def run(self) -> None:
        self._init_csv()
        keywords = self._load_keywords()
        engine = GoogleMapsEngine(headless=False)  # Set to False so you can watch progress

        console.print(f"[bold cyan]◈ Starting Google Maps Pipeline ({len(keywords)} tasks queued) ◈[/bold cyan]")

        try:
            for idx in range(self.current_idx, len(keywords)):
                kw = keywords[idx]
                console.print(f"\n[bold yellow]➜ [{idx+1}/{len(keywords)}] Searching: {kw}[/bold yellow]")

                success = engine.search_query(kw)
                if not success:
                    console.print(f"[red]Failed to open search: {kw}[/red]")
                    continue

                seen_links = set()
                scroll_attempts = 0
                max_scrolls = 15

                while scroll_attempts < max_scrolls:
                    if self.target_count > 0 and self.total_saved >= self.target_count:
                        break

                    cards = engine.extract_visible_cards()
                    for card in cards:
                        if self.target_count > 0 and self.total_saved >= self.target_count:
                            break

                        details = engine.parse_card_details(card)
                        if details and details.get("link") and details["link"] not in seen_links:
                            seen_links.add(details["link"])
                            row = [
                                kw,
                                details["title"],
                                details["category"],
                                details["phone"],
                                details["website"],
                                details["address"],
                                details["rating"],
                                details["reviews"],
                            ]
                            with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                                writer = csv.writer(f)
                                writer.writerow(row)

                            self.total_saved += 1
                            console.print(f" [green]#{self.total_saved}[/green] [white]{details['title'][:25]}[/white] | [cyan]{details['phone']}[/cyan] | [dim]{details['website'][:25]}[/dim]")

                    engine.scroll_results_pane()
                    scroll_attempts += 1

                update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)

                if self.target_count > 0 and self.total_saved >= self.target_count:
                    console.print(f"\n[bold green]✔ Target goal of {self.target_count} leads fulfilled.[/bold green]")
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Execution halted by user. Progress saved.[/yellow]")
        finally:
            engine.close()
