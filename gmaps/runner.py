import csv
import os
from typing import List
import pandas as pd
from rich.console import Console
from .scraper import GoogleMapsEngine
from utils.state_manager import update_latest_progress

console = Console()
HEADERS = ["keyword", "title", "category", "phone", "website", "address", "rating", "reviews"]


class GMapsRunner:
    def __init__(self, target_input: str, output_path: str, start_index: int = 0, target_count: int = 0):
        # Sanitize Windows file paths (strip surrounding quotes or accidental whitespace)
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

                # If file has multiple columns, join them into complete search queries
                if df.shape[1] > 1:
                    return df.apply(lambda row: " ".join(row.dropna().astype(str)), axis=1).tolist()
                else:
                    return [str(val).strip() for val in df.iloc[:, 0].dropna().tolist()]
            except Exception as e:
                console.print(f"[red]Error parsing file: {e}[/red]")
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
        
        console.print(f"[bold cyan]Launching Chrome Window for Google Maps...[/bold cyan]")
        engine = GoogleMapsEngine(headless=False)  # Explicitly visible window

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
