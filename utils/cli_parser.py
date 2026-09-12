import json
import logging
import os
from pathlib import Path
from argparse import Namespace
from typing import Any, Dict, Optional
import questionary
from rich.console import Console
from rich.panel import Panel

console = Console()
STATE_FILE = ".scraper_state.json"


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


def save_state(city: str, query: str, country: str, page: int, total_saved: int, output_path: str, target_count: int) -> None:
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


def prompt_user_wizard(existing_state: Optional[Dict[str, Any]] = None) -> Namespace:
    console.print(
        Panel.fit(
            "[bold cyan]2GIS B2B Lead Extractor[/bold cyan]\n"
            "[dim]Standalone Desktop Edition[/dim]",
            border_style="cyan",
        )
    )

    if existing_state:
        c_city = existing_state.get("city_name", "")
        c_query = existing_state.get("query_string", "")
        c_page = existing_state.get("last_page", 1)
        c_saved = existing_state.get("total_saved", 0)
        c_target = existing_state.get("target_count", 5000)

        console.print(
            f"[yellow]Previous Task Found:[/yellow] "
            f"[bold green]{c_city.title()}[/bold green] ➔ '[bold white]{c_query}[/bold white]' "
            f"([cyan]{c_saved}/{c_target}[/cyan] leads collected, Page: [cyan]{c_page}[/cyan])"
        )

        should_resume = questionary.confirm("Resume previous task?", default=True).ask()
        if should_resume:
            return Namespace(
                city_name=c_city,
                query_string=c_query,
                country=existing_state.get("country", "ae"),
                output_path=existing_state.get("output_path", get_default_download_path("2gis_leads.csv")),
                start_page=c_page + 1,
                initial_saved=c_saved,
                target_count=c_target,
                auto_recover=True,
                log=logging.INFO,
            )
        else:
            clear_state()

    city_name = questionary.select(
        "Select Target City:",
        choices=["Abu Dhabi", "Dubai", "Sharjah", "Al Ain", "Ajman", "Other (Custom)"],
        default="Abu Dhabi",
    ).ask()

    if city_name == "Other (Custom)":
        city_name = questionary.text("Enter City Name:").ask().strip().lower()
    else:
        city_name = city_name.strip().lower()

    query_string = questionary.text(
        "Enter Keyword (e.g. software, real estate, clinics):",
        validate=lambda t: True if len(t.strip()) > 0 else "Keyword required!",
    ).ask().strip()

    country = questionary.select(
        "Select Region:",
        choices=[
            questionary.Choice("UAE (2gis.ae)", value="ae"),
            questionary.Choice("Russia (2gis.ru)", value="ru"),
            questionary.Choice("Kazakhstan (2gis.kz)", value="kz"),
        ],
        default="ae",
    ).ask()

    target_str = questionary.text(
        "Target number of leads to collect (0 for unlimited):",
        default="5000",
    ).ask().strip()
    target_count = int(target_str) if target_str.isdigit() else 0

    default_file = f"{city_name}_{query_string.replace(' ', '_')}.csv"
    default_dest = get_default_download_path(default_file)

    output_path = questionary.text(
        "Save Destination (Defaults to Downloads):",
        default=default_dest,
    ).ask().strip()

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
