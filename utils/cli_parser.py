import argparse
import json
import logging
import os
from typing import Any, Dict, Optional
from .loggers import parse_log_level

STATE_FILE = ".scraper_state.json"


def load_state() -> Optional[Dict[str, Any]]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_state(city: str, query: str, country: str, page: int, total_saved: int, output_path: str) -> None:
    data = {
        "city_name": city,
        "query_string": query,
        "country": country,
        "last_page": page,
        "total_saved": total_saved,
        "output_path": output_path,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def clear_state() -> None:
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
        except Exception:
            pass


def prompt_user_wizard(existing_state: Optional[Dict[str, Any]] = None) -> argparse.Namespace:
    print("\n==================================================")
    print("        2GIS B2B Contact Scraper Interactive      ")
    print("==================================================")

    # Check for resume option
    if existing_state:
        c_city = existing_state.get("city_name", "")
        c_query = existing_state.get("query_string", "")
        c_page = existing_state.get("last_page", 1)
        c_saved = existing_state.get("total_saved", 0)

        print(f"\n[!] Previous session detected:")
        print(f"    - Target:  {c_city.title()} -> '{c_query}'")
        print(f"    - Progress: Scraped {c_saved} records (Last Page: {c_page})")

        choice = input("\nDo you want to RESUME this previous session? [Y/n]: ").strip().lower()
        if choice in ("", "y", "yes"):
            ns = argparse.Namespace(
                city_name=c_city,
                query_string=c_query,
                country=existing_state.get("country", "ae"),
                output_path=existing_state.get("output_path", "./data/raw.csv"),
                start_page=c_page + 1,
                initial_saved=c_saved,
                log=logging.INFO,
            )
            print(f"[+] Resuming from Page {ns.start_page}...\n")
            return ns
        else:
            clear_state()
            print("[+] Starting a fresh task.\n")

    # Prompt for fresh input
    default_city = "dubai"
    default_country = "ae"

    city_in = input(f"Enter City name [Default: {default_city}]: ").strip()
    city_name = city_in if city_in else default_city

    query_string = ""
    while not query_string:
        query_string = input("Enter Search Keyword (e.g. companies, supermarkets): ").strip()
        if not query_string:
            print("[x] Keyword cannot be empty.")

    country_in = input(f"Enter Country TLD (ae, ru, kz) [Default: {default_country}]: ").strip().lower()
    country = country_in if country_in else default_country

    default_output = f"./data/{city_name}_{query_string.replace(' ', '_')}.csv"
    out_in = input(f"Enter Output CSV Path [Default: {default_output}]: ").strip()
    output_path = out_in if out_in else default_output

    page_in = input("Start from page [Default: 1]: ").strip()
    start_page = int(page_in) if page_in.isdigit() and int(page_in) > 0 else 1

    return argparse.Namespace(
        city_name=city_name,
        query_string=query_string,
        country=country,
        output_path=output_path,
        start_page=start_page,
        initial_saved=0,
        log=logging.INFO,
    )


def initiate_cli_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="2GIS B2B Contact Scraper",
        description="Extracts business listings, addresses, and contact numbers from 2GIS.",
    )

    parser.add_argument("city_name", nargs="?", type=str, default=None, help="Target city (e.g., dubai)")
    parser.add_argument("query_string", nargs="?", type=str, default=None, help="Search keyword (e.g., companies)")
    parser.add_argument("-c", "--country", type=str, default="ae", help="2GIS domain (ae, ru, kz)")
    parser.add_argument("-o", "--output_path", type=str, default="./data/raw.csv", help="Path to output CSV")
    parser.add_argument("-p", "--start_page", type=int, default=1, help="Starting page number")
    parser.add_argument("-l", "--log", type=parse_log_level, default=logging.INFO, help="Log level")

    args = parser.parse_args()
    state = load_state()

    # If run without arguments, switch to the interactive wizard
    if args.city_name is None and args.query_string is None:
        return prompt_user_wizard(existing_state=state)

    # If only keyword was passed as the first positional argument
    if args.city_name is not None and args.query_string is None:
        args.query_string = args.city_name
        args.city_name = "dubai"

    args.initial_saved = 0
    return args
