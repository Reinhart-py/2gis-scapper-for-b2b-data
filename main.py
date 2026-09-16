import argparse
import logging
import os
import sys

CYAN = "\033[96m"
MAGENTA = "\033[95m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def render_banner():
    clear_screen()
    print(CYAN + BOLD + r"""
  _                    _    ____              ____  _       _    __                         
 | |    ___  __ _   __| |  / ___| ___ _ __   |  _ \| | __ _| |_ / _| ___  _ __ _ __ ___  
 | |   / _ \/ _` | / _` | | |  _ / _ \ '_ \  | |_) | |/ _` | __| |_ / _ \| '__| '_ ` _ \ 
 | |__|  __/ (_| || (_| | | |_| |  __/ | | | |  __/| | (_| | |_|  _| (_) | |  | | | | | |
 |_____\___|\__,_| \__,_|  \____|\___|_| |_| |_|   |_|\__,_|\__|_|  \___/|_|  |_| |_| |_|
    """ + RESET)


def handle_2gis(args):
    from utils import initiate_logger
    from runner import Runner

    initiate_logger(args.log)
    runner = Runner(config=args)
    runner.run()


def handle_gmap(args):
    import gmaps_scraper

    if args.interactive or (not args.query and not args.file and not args.resume):
        gmaps_scraper.main()
        return

    out_file = args.output_path or gmaps_scraper.DEFAULT_OUTPUT
    workers = args.workers

    if args.resume:
        history = gmaps_scraper.load_history()
        if not history:
            print(f"{YELLOW}No saved sessions found to resume.{RESET}")
            return
        sel = history[0]
        targets = sel.get("targets", [])
        completed = sel.get("completed_index", 0)
        sess_name = sel.get("session_name", "resumed_cli")
        gmaps_scraper.execute_scraping_job_parallel(sess_name, targets, completed, out_file, workers)
        return

    targets = []
    if args.file:
        targets = gmaps_scraper.parse_input_file(args.file)
        if not targets:
            print(f"{YELLOW}No valid targets found in file: {args.file}{RESET}")
            return
    elif args.query:
        targets = [" ".join(args.query)]

    sess_name = f"cli_job_{os.getpid()}"
    gmaps_scraper.execute_scraping_job_parallel(sess_name, targets, 0, out_file, workers)


def interactive_menu():
    while True:
        render_banner()
        print(f"{BOLD}SELECT SCRAPING ENGINE{RESET}")
        print("1. 2GIS B2B Scraper (UAE, Russia, Central Asia)")
        print("2. Google Maps Global Scraper (Parallel Workers & Anti-Bot)")
        print("3. About / Architect Info")
        print("4. Exit")

        choice = input(f"\n{CYAN}Select an option (1-4): {RESET}").strip()

        if choice == "1":
            from argparse import Namespace
            from runner import Runner

            render_banner()
            city = input(f"{YELLOW}Enter City (e.g., dubai, moscow): {RESET}").strip()
            if not city:
                continue
            query = input(f"{YELLOW}Enter Keyword(s) (e.g., travel agencies): {RESET}").strip()
            if not query:
                continue
            country = input(f"{YELLOW}Country TLD [default: ae]: {RESET}").strip() or "ae"
            out = input(f"{YELLOW}Output CSV [default: ./data/raw.csv]: {RESET}").strip() or "./data/raw.csv"

            conf = Namespace(
                city_name=city,
                query_string=query.split(),
                country=country,
                output_path=out,
            )
            runner = Runner(config=conf)
            runner.run()
            input(f"\n{CYAN}Press Enter to return...{RESET}")

        elif choice == "2":
            import gmaps_scraper
            gmaps_scraper.main()

        elif choice == "3":
            import gmaps_scraper
            gmaps_scraper.render_architect()

        elif choice == "4":
            clear_screen()
            print(MAGENTA + "\n  Late night? Go sleep.\n" + RESET)
            sys.exit(0)


def build_cli_parser():
    from utils.loggers import parse_log_level

    parser = argparse.ArgumentParser(
        prog="LeadGen Multi-Tool",
        description="Unified Lead Generation Scraper for 2GIS and Google Maps",
    )
    subparsers = parser.add_subparsers(dest="engine", help="Choose scraping engine")

    # --- 2GIS Parser ---
    p_2gis = subparsers.add_parser("2gis", help="Run 2GIS scraper")
    p_2gis.add_argument("city_name", type=str, help="Target city (e.g., dubai, moscow)")
    p_2gis.add_argument("query_string", type=str, nargs="+", help="Search keyword(s)")
    p_2gis.add_argument("-c", "--country", type=str, default="ae", help="Country TLD (ae, ru, kz)")
    p_2gis.add_argument("-o", "--output_path", type=str, default="./data/raw.csv", help="Output CSV path")
    p_2gis.add_argument("-l", "--log", type=parse_log_level, default=logging.INFO, help="Log level")
    p_2gis.set_defaults(func=handle_2gis)

    # --- Google Maps Parser ---
    p_gmap = subparsers.add_parser("gmap", help="Run Google Maps scraper")
    p_gmap.add_argument("query", type=str, nargs="*", default=None, help="Search query or direct URL")
    p_gmap.add_argument("-f", "--file", type=str, default=None, help="Batch input file (.txt, .csv, .xlsx)")
    p_gmap.add_argument("-w", "--workers", type=int, default=1, help="Number of parallel Chrome browser instances")
    p_gmap.add_argument("-o", "--output_path", type=str, default="./data/gmaps_leads.csv", help="Output CSV path")
    p_gmap.add_argument("-r", "--resume", action="store_true", help="Auto-resume latest saved checkpoint")
    p_gmap.add_argument("-i", "--interactive", action="store_true", help="Launch interactive Google Maps UI")
    p_gmap.set_defaults(func=handle_gmap)

    return parser


def main():
    if len(sys.argv) == 1:
        interactive_menu()
        return

    parser = build_cli_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
