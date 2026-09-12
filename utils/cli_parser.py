import json
import logging
import os
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, Optional

import questionary
from questionary import Style
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .loggers import parse_log_level

console = Console()
STATE_FILE = ".scraper_state.json"

# Premium custom style for questionary prompts
CUSTOM_STYLE = Style([
    ("qmark", "fg:#00ffff bold"),
    ("question", "fg:#ffffff bold"),
    ("answer", "fg:#39ff14 bold"),
    ("pointer", "fg:#ff007f bold"),
    ("highlighted", "fg:#00ffff bold underline"),
    ("selected", "fg:#39ff14"),
    ("separator", "fg:#555555"),
    ("instruction", "fg:#777777 italic"),
    ("text", "fg:#eeeeee"),
])


def get_default_download_path(filename: str) -> str:
    downloads = Path.home() / "Downloads"
    return str(downloads / filename)


def load_state() -> Optional[Dict[str, Any]]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_state(
    city: str,
    query: str,
    country: str,
    page: int,
    total_saved: int,
    output_path: str,
    target_count: int,
) -> None:
    data = {
        "city_name": city,
        "query_string": query,
        "country": country,
        "last_page": page,
        "total_saved": total_saved,
        "output_path": output_path,
        "target_count": target_count,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def clear_state() -> None:
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass


def render_banner() -> None:
    console.clear()
    
    ascii_art = """
 ██████╗  ██████╗ ██╗███████╗    ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗ 
██╔════╝ ██╔════╝ ██║██╔════╝    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
╚█████╗  ██║  ███╗██║███████╗    ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
 ╚════██╗██║   ██║██║╚════██║    ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
██████╔╝╚██████╔╝██║███████║    ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
╚═════╝  ╚═════╝ ╚═╝╚══════╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
    """
    
    gradient_text = Text(ascii_art)
    gradient_text.stylize("bold cyan")

    author_markup = (
        "[dim]⚡ Built for high-volume, reliable B2B extraction[/dim]\n\n"
        "[bold white]Developed by: [/bold white]"
        "[link=https://reinhart.pages.dev/][bold magenta underline]Reinhart aka kiri[/bold magenta underline][/link]"
    )

    panel = Panel(
        Align.center(gradient_text),
        title="[bold #39ff14]◈ v0.2.0 • CORE EDITION ◈[/bold #39ff14]",
        subtitle=author_markup,
        subtitle_align="center",
        border_style="bold #00e5ff",
        padding=(0, 2),
    )
    console.print(panel)
    console.print("")


def prompt_user_wizard(existing_state: Optional[Dict[str, Any]] = None) -> Namespace:
    render_banner()

    # Session recovery prompt
    if existing_state:
        c_city = existing_state.get("city_name", "unknown")
        c_query = existing_state.get("query_string", "unknown")
        c_page = existing_state.get("last_page", 1)
        c_saved = existing_state.get("total_saved", 0)
        c_target = existing_state.get("target_count", 0)
        c_dest = existing_state.get("output_path", "./data/raw.csv")

        table = Table(title="◈ UNFINISHED MISSION DETECTED ◈", border_style="cyan", show_header=False)
        table.add_column("Field", style="bold yellow")
        table.add_column("Value", style="bold white")

        target_label = f"{c_target} leads" if c_target > 0 else "Unlimited"
        table.add_row("City / Region", c_city.title())
        table.add_row("Keyword", c_query)
        table.add_row("Progress", f"{c_saved} leads (Stopped at Page {c_page})")
        table.add_row("Target", target_label)
        table.add_row("Destination", c_dest)

        console.print(table)
        console.print("")

        should_resume = questionary.confirm(
            "Resume previous scraping mission?",
            default=True,
            style=CUSTOM_STYLE,
        ).ask()

        if should_resume:
            return Namespace(
                city_name=c_city,
                query_string=c_query,
                country=existing_state.get("country", "ae"),
                output_path=c_dest,
                start_page=c_page + 1,
                initial_saved=c_saved,
                target_count=c_target,
                auto_recover=True,
                log=logging.INFO,
            )
        else:
            clear_state()
            console.print("[dim yellow]✦ Session state purged. Launching configuration wizard...[/dim yellow]\n")

    # Step 1: Target City
    city_name = questionary.select(
        "Select Target City:",
        choices=[
            "Abu Dhabi",
            "Dubai",
            "Sharjah",
            "Al Ain",
            "Ajman",
            "Other (Custom)",
        ],
        default="Abu Dhabi",
        style=CUSTOM_STYLE,
    ).ask()

    if not city_name:
        raise SystemExit(0)

    if city_name == "Other (Custom)":
        city_name = questionary.text("Enter City Name:", style=CUSTOM_STYLE).ask().strip().lower()
    else:
        city_name = city_name.strip().lower()

    # Step 2: Query String
    query_string = questionary.text(
        "Enter Target Keyword (e.g., software, restaurants, clinics):",
        validate=lambda t: True if len(t.strip()) > 0 else "Keyword cannot be empty!",
        style=CUSTOM_STYLE,
    ).ask().strip()

    # Step 3: Domain
    country = questionary.select(
        "Select 2GIS Regional Domain:",
        choices=[
            questionary.Choice("UAE (2gis.ae)", value="ae"),
            questionary.Choice("Russia (2gis.ru)", value="ru"),
            questionary.Choice("Kazakhstan (2gis.kz)", value="kz"),
        ],
        default="ae",
        style=CUSTOM_STYLE,
    ).ask()

    # Step 4: Target Leads
    target_str = questionary.text(
        "Target number of leads to collect (0 for unlimited):",
        default="5000",
        style=CUSTOM_STYLE,
    ).ask().strip()
    target_count = int(target_str) if target_str.isdigit() else 0

    # Step 5: Save Destination
    default_filename = f"{city_name}_{query_string.replace(' ', '_')}.csv"
    default_dest = get_default_download_path(default_filename)

    output_path = questionary.text(
        "Output CSV Path (Defaults directly to Downloads):",
        default=default_dest,
        style=CUSTOM_STYLE,
    ).ask().strip()

    console.print("\n[bold green]✔ Parameters initialized! Spawning Chromium engine...[/bold green]\n")

    return Namespace(
        city_name=city_name,
        query_string=query_string,
        country=country,
        output_path=output_path,
        start_page=1,
        initial_saved=0,
        target_count=target_count,
        auto_recover=True,
        log=logging.INFO,
    )


def initiate_cli_parser() -> Namespace:
    state = load_state()
    return prompt_user_wizard(existing_state=state)
