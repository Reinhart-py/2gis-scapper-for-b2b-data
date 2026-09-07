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
    parser.add_argument(
        "query_string",
        type=str,
        help="Search keyword (e.g., supermarkets, software)",
    )
    parser.add_argument(
        "-c",
        "--country",
        type=str,
        default="ae",
        help="2GIS top-level domain country code: 'ae' for UAE, 'ru' for Russia, 'kz' for Kazakhstan. Default: 'ae'",
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
