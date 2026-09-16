import logging
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import Optional

import questionary
from questionary import Style
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .state_manager import load_all_history, push_history_checkpoint

console = Console()

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


def render_banner() -> None:
    console.clear()
    ascii_art = """
 ██████╗ ███████╗██████╗  ██████╗ ██████╗     ███████╗██╗   ██╗██╗████████╗███████╗
██╔════╝ ██╔════╝██╔══██╗██╔═══██╗██╔══██╗    ██╔════╝██║   ██║██║╚══██╔══╝██╔════╝
██║  ███╗█████╗  ██████╔╝██║   ██║██████╔╝    ███████╗██║   ██║██║   ██║   █████╗  
██║   ██║██╔══╝  ██╔══██╗██║   ██║██╔═══╝     ╚════██║██║   ██║██║   ██║   ██╔══╝  
╚██████╔╝███████╗██████╔╝╚██████╔╝██║         ███████║╚██████╔╝██║   ██║   ███████╗
 ╚═════╝ ╚══════╝╚═════╝  ╚═════╝ ╚═╝         ╚══════╝ ╚═════╝ ╚═╝   ╚═╝   ╚══════╝
    """
    gradient_text = Text(ascii_art)
    gradient_text.stylize("bold cyan")

    panel = Panel(
        Align.center(gradient_text),
        title="[bold #39ff14]◈ DUAL-ENGINE INTELLIGENCE v0.3.0 ◈[/bold #39ff14]",
        subtitle="[bold white]Developed by: [/bold white][link=https://reinhart.pages.dev/][bold magenta underline]Reinhart aka kiri[/bold magenta underline][/link]",
        subtitle_align="center",
        border_style="bold #00e5ff",
        padding=(0, 2),
    )
    console.print(panel)


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
    console.print(Panel(Align.center(text), border_style="magenta"))
    questionary.press_any_key_to_continue(message="Press any key to return...").ask()


def history_menu() -> Optional[Namespace]:
    history = load_all_history()
    if not history:
        console.print("[yellow]No execution checkpoints recorded yet.[/yellow]")
        questionary.press_any_key_to_continue().ask()
        return None

    table = Table(title="◈ LAST 10 EXECUTION CHECKPOINTS ◈", border_style="cyan")
    table.add_column("Index", style="bold yellow")
    table.add_column("Engine", style="bold green")
    table.add_column("Target / Query", style="white")
    table.add_column("Checkpoint", style="cyan")
    table.add_column("Collected", style="bold magenta")

    choices = []
    for idx, item in enumerate(history):
        table.add_row(
            str(idx + 1),
            item.get("engine", "unknown").upper(),
            str(item.get("target", ""))[:30],
            f"Step/Page {item.get('last_step', 1)}",
            f"{item.get('total_saved', 0)} leads",
        )
        choices.append(questionary.Choice(
            title=f"[{item.get('engine').upper()}] {item.get('target')} (Saved: {item.get('total_saved')})",
            value=item,
        ))

    console.print(table)
    choices.append(questionary.Choice(title="[Back to Main Menu]", value="BACK"))

    selected = questionary.select("Select a checkpoint to resume:", choices=choices, style=CUSTOM_STYLE).ask()
    if selected == "BACK" or not selected:
        return None

    return Namespace(
        engine=selected["engine"],
        target=selected["target"],
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
        "Select Target City:",
        choices=["Abu Dhabi", "Dubai", "Sharjah", "Al Ain", "Ajman", "Other (Custom)", "[Back]"],
        style=CUSTOM_STYLE,
    ).ask()
    if city == "[Back]" or not city:
        return None

    if city == "Other (Custom)":
        city = questionary.text("Enter City Name:", style=CUSTOM_STYLE).ask().strip().lower()
    else:
        city = city.strip().lower()

    query = questionary.text("Enter Keyword (e.g. software, hotels):", style=CUSTOM_STYLE).ask().strip()
    country = questionary.select("Select Domain:", choices=[
        questionary.Choice("UAE (2gis.ae)", value="ae"),
        questionary.Choice("Russia (2gis.ru)", value="ru"),
        questionary.Choice("Kazakhstan (2gis.kz)", value="kz"),
    ], style=CUSTOM_STYLE).ask()

    target_str = questionary.text("Target leads limit (0 for unlimited):", default="2000", style=CUSTOM_STYLE).ask()
    target_count = int(target_str) if target_str.isdigit() else 0
    dest = get_default_download_path(f"2gis_{city}_{query.replace(' ', '_')}.csv")
    output_path = questionary.text("Output CSV Destination:", default=dest, style=CUSTOM_STYLE).ask().strip()

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
        "Select Google Maps Input Method:",
        choices=[
            "Single Search Query (e.g. 'Coffee in Dubai')",
            "Batch Keywords File (.txt, .csv, .xlsx)",
            "Direct Google Maps Search URL",
            "[Back]",
        ],
        style=CUSTOM_STYLE,
    ).ask()

    if input_type == "[Back]" or not input_type:
        return None

    if "Single Search" in input_type or "Direct Google" in input_type:
        target = questionary.text("Enter Search Query or Maps URL:", style=CUSTOM_STYLE).ask().strip()
    else:
        target = questionary.text("Enter Path to (.txt / .csv / .xlsx) Keyword File:", style=CUSTOM_STYLE).ask().strip()

    target_str = questionary.text("Target leads count (0 for unlimited):", default="1000", style=CUSTOM_STYLE).ask()
    target_count = int(target_str) if target_str.isdigit() else 0
    dest = get_default_download_path("gmaps_leads.csv")
    output_path = questionary.text("Output CSV Destination:", default=dest, style=CUSTOM_STYLE).ask().strip()

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
            "COMMAND ROOT:",
            choices=[
                "1. Google Maps Extractor (Keywords / Files / URLs)",
                "2. 2GIS Lead Generator (UAE & Multi-Region)",
                "3. Checkpoint Vault (Last 10 Session Resumes)",
                "4. Architect Profile & Contacts",
                "5. Exit Suite",
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
