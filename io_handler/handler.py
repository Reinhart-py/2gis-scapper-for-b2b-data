import csv
import logging
from utils import ColumnData

HEADERS = ["title", "phone_1", "phone_2", "phone_3", "address"]


def write_csv_headers(file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        f.flush()


def append_single_row(file_path: str, row: list) -> None:
    with open(file_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)
        f.flush()


def write_to_csv(page_number: int, data: ColumnData, file_path: str) -> None:
    with open(file_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for m in range(len(data.title)):
            writer.writerow([
                data.title[m],
                data.phone_1[m],
                data.phone_2[m],
                data.phone_3[m],
                data.address[m],
            ])
        f.flush()
    logging.info(f"PAGE {page_number} WRITTEN TO CSV")


def write_to_file(file_path: str, content: str) -> None:
    with open(file_path, "w", encoding="utf-8") as writable_file:
        writable_file.write(content)
