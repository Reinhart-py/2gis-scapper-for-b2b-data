python -c "content = '''# 2GIS B2B Lead & Contact Scraper

A lightweight, automated lead-generation tool to extract business names, addresses, and multiple phone numbers (split into separate columns) from [2GIS](https://2gis.ae).

Built on Selenium WebDriver, it handles dynamic drawer rendering, unmasks contact details behind \"Show phone number\" buttons, and immediately flushes data to disk line-by-line.

---

## Features

- Multi-Phone Extraction: Automatically separates primary and alternative contact lines into phone_1, phone_2, and phone_3.
- Country Priority Sorting: Intelligently prioritizes official country-code prefixes (e.g., +971) into phone_1.
- Dynamic Unmasking: Automatically detects and triggers hidden contact reveal buttons.
- Fail-Safe Stream Writing: Appends and flushes each row directly to CSV in real time; stopping execution (Ctrl + C) never loses saved records.
- Multi-Region Support: Switch between 2gis.ae, 2gis.ru, 2gis.kz, etc., using the -c flag.

---

## Output Format (./data/raw.csv)

| title | phone_1 | phone_2 | phone_3 | address |
|---|---|---|---|---|
| Union Co-operative Society | +97143200000 | +97143200001 | 8008889 | Ras Al Khor Industrial 3, Dubai |
| IT Bits Software & Events | +97142879755 | null | null | The Metropolis, Marasi Drive, Business Bay, Dubai |

---

## Requirements

- Python 3.11+
- Google Chrome (latest)
- ChromeDriver (automatically handled by Selenium)

---

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Reinhart-py/2gis-scapper-for-b2b-data.git
   cd 2gis-scapper-for-b2b-data```

2. Create and activate a virtual environment:
Windows (CMD):
    ```
    python -m venv .venv
    call .venv\Scripts\activate```

Linux / macOS:
     ```
     python3 -m venv .venv
     source .venv/bin/activate```

3. Install dependencies:
  ```
  pip install -r requirements.txt ```

---

## Usage

python main.py <city_name> <query_string> [options]

### CLI Options

| Argument | Type | Default | Description |
|---|---|---|---|
| city_name | positional | required | City name (e.g., dubai, moscow, almaty) |
| query_string | positional | required | Business category or term (e.g., supermarkets, software) |
| -c, --country | optional | ae | 2GIS regional domain: ae (UAE), ru (Russia), kz (Kazakhstan) |
| -o, --output_path | optional | ./data/raw.csv | Destination path for the output CSV file |
| -l, --log | optional | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Examples

# Scrape supermarkets in Dubai (UAE)
python main.py dubai supermarkets

# Scrape coffee shops in Moscow on 2gis.ru
python main.py moscow coffee -c ru

# Scrape hotels in Almaty with a custom CSV path
python main.py almaty hotels -c kz -o ./data/almaty_hotels.csv

---

## Cleaned Project Structure

2gis-scapper-for-b2b-data/
|-- data/
|   `-- raw.csv
|-- executor/
|   |-- __init__.py
|   `-- executor.py
|-- io_handler/
|   |-- __init__.py
|   `-- handler.py
|-- runner/
|   |-- __init__.py
|   `-- runner.py
|-- utils/
|   |-- __init__.py
|   |-- cli_parser.py
|   |-- loggers.py
|   |-- types.py
|   `-- utils.py
|-- main.py
|-- requirements.txt
|-- LICENSE.md
`-- README.md

---

## License

Distributed under the Apache License 2.0.
'''; open('README.md', 'w', encoding='utf-8').write(content)"
