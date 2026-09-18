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
        
        console.print("[bold cyan]Spawning Chrome engine...[/bold cyan]")
        engine = GoogleMapsEngine(headless=False)
        console.print(f"[bold cyan]◈ Commencing Queue: {len(keywords)} tasks loaded ◈[/bold cyan]")

        try:
            for idx in range(self.current_idx, len(keywords)):
                kw = keywords[idx]
                console.print(f"\n[bold yellow]➜ [{idx+1}/{len(keywords)}] Keyword: {kw}[/bold yellow]")

                success = engine.search_query(kw)
                if not success:
                    console.print(f"[red]Failed to open query: {kw}[/red]")
                    continue

                seen_links = set()
                stagnant_scroll_count = 0
                max_scrolls = 25

                # Check if Google directly opened a single place page instead of list
                if engine.is_single_place_view():
                    console.print(f"[dim cyan]Single business page detected for '{kw}'[/dim cyan]")
                    details = engine.parse_active_place_pane()
                    if details and details["title"] != "null":
                        row = [
                            kw, details["title"], details["category"], details["phone"],
                            details["website"], details["address"], details["rating"], details["reviews"]
                        ]
                        with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                            csv.writer(f).writerow(row)
                        self.total_saved += 1
                        console.print(f" [green]#{self.total_saved}[/green] [white]{details['title'][:25]}[/white] | [cyan]{details['phone']}[/cyan]")
                    
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
                                    kw, details["title"], details["category"], details["phone"],
                                    details["website"], details["address"], details["rating"], details["reviews"]
                                ]
                                with open(self.output_path, "a", encoding="utf-8", newline="") as f:
                                    csv.writer(f).writerow(row)

                                self.total_saved += 1
                                new_cards_found += 1
                                console.print(f" [green]#{self.total_saved}[/green] [white]{details['title'][:25]}[/white] | [cyan]{details['phone']}[/cyan] | [dim]{details['website'][:25]}[/dim]")
                        except Exception:
                            continue

                    # 1. Check if Google rendered the end badge
                    if engine.is_end_of_list():
                        console.print("[dim cyan]Reached the end of list for this keyword. Progressing to next...[/dim cyan]")
                        break

                    # 2. Track stagnant scrolling (no new items rendered)
                    has_moved, _ = engine.scroll_results_pane()
                    if new_cards_found == 0 and not has_moved:
                        stagnant_scroll_count += 1
                    else:
                        stagnant_scroll_count = 0

                    if stagnant_scroll_count >= 2:
                        console.print("[dim cyan]No further records loading. Advancing to next keyword...[/dim cyan]")
                        break

                update_latest_progress("gmaps", self.target_input, idx + 1, self.total_saved)

                if self.target_count > 0 and self.total_saved >= self.target_count:
                    console.print(f"\n[bold green]✔ Target goal of {self.target_count} leads reached.[/bold green]")
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Execution paused by user. State secured.[/yellow]")
        finally:
            engine.close()
