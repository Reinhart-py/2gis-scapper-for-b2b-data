import argparse
import logging
from .loggers import parse_log_level


def initiate_cli_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="2GIS B2B Contact Scraper",
        description="Extracts business listings, addresses, and contact numbers from 2GIS.",
        exit_on_error=True,
    )

    parser.add_argument(
        "city_name",
        type=str,
        help="Target city (e.g., dubai, moscow, almaty)",
    )
    # nargs='+' captures all remaining words into a single query list
    parser.add_argument(
        "query_string",
        type=str,
        nargs="+",
        help="Search keyword(s) (e.g., travel agencies, real estate, software)",
    )
    parser.add_argument(
        "-c",
        "--country",
        type=str,
        default="ae",
        help="2GIS regional domain code: ae (UAE), ru (Russia), kz (Kazakhstan). Default: ae",
    )
    parser.add_argument(
        "-o",
        "--output_path",
        type=str,
        default="./data/raw.csv",
        help="Path to output CSV file. Default: ./data/raw.csv",
    )
    parser.add_argument(
        "-l",
        "--log",
        type=parse_log_level,
        default=logging.INFO,
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO",
    )

    return parser.parse_args()
