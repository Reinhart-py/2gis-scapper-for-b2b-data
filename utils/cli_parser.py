import logging
import os
import sys
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
from rich.box import ROUNDED, DOUBLE_EDGE

from .state_manager import load_all_history, push_history_checkpoint

console = Console()
STATE_FILE = ".scraper_state.json"

CUSTOM_STYLE = Style([
    ("qmark", "fg:#00f0ff bold"),
    ("question", "fg:#ffffff bold"),
    ("answer", "fg:#00ff66 bold"),
    ("pointer", "fg:#ff007f bold"),
    ("highlighted", "fg:#00f0ff bold underline"),
    ("selected", "fg:#00ff66 bold"),
    ("separator", "fg:#3a3a4c"),
    ("instruction", "fg:#6272a4 italic"),
    ("text", "fg:#f8f8f2"),
])


def get_default_download_path(filename: str) -> str:
    downloads = Path.home() / "Downloads"
    return str(downloads / filename)


def save_state(city: str, query: str, country: str, page: int, total_saved: int, output_path: str, target_count: int) -> None:
    push_history_checkpoint({
        "engine": "2gis",
        "target": f"{city}:{query}",
        "city_name": city,
        "query_string": query,
        "country": country,
        "output_path": output_path,
        "last_step": page,
        "total_saved": total_saved,
        "target_count": target_count,
    })


def clear_state() -> None:
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass


def render_banner() -> None:
    console.clear()
    
    header_art = """
 ██████╗ ███████╗██████╗  ██████╗ ██████╗     ███████╗██╗   ██╗██╗████████╗███████╗
██╔════╝ ██╔════╝██╔══██╗██╔═══██╗██╔══██╗    ██╔════╝██║   ██║██║╚══██╔══╝██╔════╝
██║  ███╗█████╗  ██████╔╝██║   ██║██████╔╝    ███████╗██║   ██║██║   ██║   █████╗  
██║   ██║██╔══╝  ██╔══██╗██║   ██║██╔═══╝     ╚════██║██║   ██║██║   ██║   ██╔══╝  
╚██████╔╝███████╗██████╔╝╚██████╔╝██║         ███████║╚██████╔╝██║   ██║   ███████╗
 ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝         ╚══════╝ ╚═════╝ ╚═╝   ╚═╝   ╚══════╝
    """
    banner_text = Text(header_art)
    banner_text.stylize("bold cyan")

    status_table = Table(box=ROUNDED, border_style="#3a3a4c", show_header=False, expand=True)
    status_table.add_column("Key", style="bold #ff007f", width=22)
    status_table.add_column("Val", style="bold white")

    status_table.add_row("◈ ARCHITECTURE", "High-Throughput Lead Intelligence System (Dual Engine)")
    status_table.add_row("◈ RATE-LIMIT BYPASS", "Active Human-Emulation Jitter + 20s Dynamic Sentry")
    status_table.add_row("◈ MOBILE DETECTION", "Direct Mobile Extraction Prioritization (+9715 / Global)")
    status_table.add_row("◈ LEAD DEVELOPER", "[link=https://reinhart.pages.dev/][bold #00f0ff underline]Reinhart aka kiri[/bold #00f0ff underline][/link] | [dim]Portfolio Attached[/dim]")

    console.print(
        Panel(
            Align.center(banner_text),
            title="[bold #00ff66]⚡ GEBOP ENTERPRISE v4.0.0 ⚡[/bold #00ff66]",
            border_style="bold #00f0ff",
            box=DOUBLE_EDGE,
            padding=(0, 1),
        )
    )
    console.print(status_table)
    console.print("")


def display_architect_info() -> None:
    console.clear()
    text = """
[bold #DEADED]
    THE ARCHITECT
    =============
    
    Reinhart aka kiri
    -----------------
    Website:   https://reinhart.pages.dev/
    Telegram:  @kiri0507
    Instagram: @reinhart.dev
    
    "We do not do it because it's easy.
     We do it because we thought it would be easy."
[/bold #DEADED]
    """
    console.print(Panel(Align.center(text), title="[bold #ff007f]◈ SYSTEM PROFILE ◈[/bold #ff007f]", border_style="#ff007f", box=ROUNDED))
    questionary.press_any_key_to_continue(message="Press any key to return...").ask()


def history_menu() -> Optional[Namespace]:
    history = load_all_history()
    if not history:
        console.print("[yellow]✦ Checkpoint vault is currently empty.[/yellow]")
        questionary.press_any_key_to_continue().ask()
        return None

    table = Table(title="◈ CHECKPOINT RESTORATION VAULT (LAST 10 SESSIONS) ◈", border_style="bold #00f0ff", box=ROUNDED)
    table.add_column("ID", style="bold yellow", width=4)
    table.add_column("ENGINE", style="bold green", width=10)
    table.add_column("TARGET SOURCE", style="white", width=35)
    table.add_column("STEP / PAGE", style="cyan", width=14)
    table.add_column("HARVESTED", style="bold magenta")

    choices = []
    for idx, item in enumerate(history):
        table.add_row(
            str(idx + 1),
            item.get("engine", "unknown").upper(),
            str(item.get("target", ""))[:32],
            f"Step {item.get('last_step', 1)}",
            f"{item.get('total_saved', 0)} leads",
        )
        choices.append(questionary.Choice(
            title=f"[{item.get('engine').upper()}] {item.get('target')} ({item.get('total_saved')} collected)",
            value=item,
        ))

    console.print(table)
    choices.append(questionary.Choice(title="[Back to Control Center]", value="BACK"))

    selected = questionary.select("Select checkpoint to resume execution:", choices=choices, style=CUSTOM_STYLE).ask()
    if selected == "BACK" or not selected:
        return None

    return Namespace(
        engine=selected["engine"],
        target=selected.get("target", ""),
        city_name=selected.get("city_name", "dubai"),
        query_string=selected.get("query_string", ""),
        country=selected.get("country", "ae"),
        output_path=selected.get("output_path", get_default_download_path("export.csv")),
        start_step=selected.get("last_step", 1),
        initial_saved=selected.get("total_saved", 0),
        target_count=selected.get("target_count", 0),
    )


def prompt_2gis_wizard() -> Optional[Namespace]:
    city = questionary.select(
        "Select Target Region / Emirate:",
        choices=["Abu Dhabi", "Dubai", "Sharjah", "Al Ain", "Ajman", "Custom Query Entry", "[Back]"],
        style=CUSTOM_STYLE,
    ).ask()
    if city == "[Back]" or not city:
        return None

    if city == "Custom Query Entry":
        city = questionary.text("Enter Custom City/Region Name:", style=CUSTOM_STYLE).ask().strip().lower()
    else:
        city = city.strip().lower()

    query = questionary.text("Enter Search Keyword (e.g. software companies, cafes, clinics):", style=CUSTOM_STYLE).ask().strip()
    country = questionary.select("Select Domain System:", choices=[
        questionary.Choice("UAE (2gis.ae)", value="ae"),
        questionary.Choice("Russia (2gis.ru)", value="ru"),
        questionary.Choice("Kazakhstan (2gis.kz)", value="kz"),
    ], style=CUSTOM_STYLE).ask()

    target_str = questionary.text("Target leads cap (0 for continuous operation):", default="2000", style=CUSTOM_STYLE).ask()
    target_count = int(target_str) if target_str.isdigit() else 0
    dest = get_default_download_path(f"2gis_{city}_{query.replace(' ', '_')}.csv")
    output_path = questionary.text("Export CSV File Destination:", default=dest, style=CUSTOM_STYLE).ask().strip()

    push_history_checkpoint({
        "engine": "2gis",
        "target": f"{city}:{query}",
        "city_name": city,
        "query_string": query,
        "country": country,
        "output_path": output_path,
        "last_step": 1,
        "total_saved": 0,
        "target_count": target_count,
    })

    return Namespace(
        engine="2gis",
        city_name=city,
        query_string=query,
        country=country,
        output_path=output_path,
        start_step=1,
        initial_saved=0,
        target_count=target_count,
    )


def prompt_gmaps_wizard() -> Optional[Namespace]:
    input_type = questionary.select(
        "Select Google Maps Input Vector:",
        choices=[
            "Single Search Query (e.g. 'Software in Business Bay')",
            "Batch File Processing (.csv, .xlsx, .txt)",
            "Direct Google Maps Custom Place URL",
            "[Back]",
        ],
        style=CUSTOM_STYLE,
    ).ask()

    if input_type == "[Back]" or not input_type:
        return None

    if "Single Search" in input_type or "Direct Google" in input_type:
        target = questionary.text("Enter Target Query or Maps Web URL:", style=CUSTOM_STYLE).ask().strip()
    else:
        target = questionary.text("Paste Path to Batch File (Tip: Drag & Drop file here):", style=CUSTOM_STYLE).ask().strip()

    target_str = questionary.text("Target leads cap (0 for continuous extraction):", default="1000", style=CUSTOM_STYLE).ask()
    target_count = int(target_str) if target_str.isdigit() else 0
    dest = get_default_download_path("gmaps_leads.csv")
    output_path = questionary.text("Export CSV File Destination:", default=dest, style=CUSTOM_STYLE).ask().strip()

    push_history_checkpoint({
        "engine": "gmaps",
        "target": target,
        "output_path": output_path,
        "last_step": 0,
        "total_saved": 0,
        "target_count": target_count,
    })

    return Namespace(
        engine="gmaps",
        target=target,
        output_path=output_path,
        start_step=0,
        initial_saved=0,
        target_count=target_count,
    )


def initiate_cli_parser() -> Namespace:
    while True:
        render_banner()
        main_choice = questionary.select(
            "PRIMARY ACTION DISPATCHER:",
            choices=[
                "1. Google Maps Lead Miner (Batch Files / Queries / URLs)",
                "2. 2GIS Lead Generator (Emirates & Multi-Country)",
                "3. Checkpoint Vault (Restore Any of Last 10 Sessions)",
                "4. Architect Profile & Intelligence Dossier",
                "5. Terminate Session",
            ],
            style=CUSTOM_STYLE,
        ).ask()

        if main_choice.startswith("1."):
            cfg = prompt_gmaps_wizard()
            if cfg:
                return cfg
        elif main_choice.startswith("2."):
            cfg = prompt_2gis_wizard()
            if cfg:
                return cfg
        elif main_choice.startswith("3."):
            cfg = history_menu()
            if cfg:
                return cfg
        elif main_choice.startswith("4."):
            display_architect_info()
        else:
            console.print("[dim magenta]Late night? Go sleep.[/dim magenta]")
            sys.exit(0)
