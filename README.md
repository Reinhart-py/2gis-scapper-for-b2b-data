# 2GIS B2B Lead & Contact Scraper

A lightweight, automated lead-generation tool to extract business names, addresses, and multiple phone numbers (split into separate columns) from [2GIS](https://2gis.ae). 

Built on Selenium WebDriver, it handles dynamic drawer rendering, unmasks contact details behind "Show phone number" buttons, and immediately flushes data to disk line-by-line.

---

## Features

- **Multi-Phone Extraction**: Automatically separates primary and alternative contact lines into `phone_1`, `phone_2`, and `phone_3`.
- **Country Priority Sorting**: Intelligently prioritizes official country-code prefixes (e.g., `+971`) into `phone_1`.
- **Dynamic Unmasking**: Automatically detects and triggers hidden contact reveal buttons.
- **Fail-Safe Stream Writing**: Appends and flushes each row directly to CSV in real time; stopping execution (`Ctrl + C`) never loses saved records.
- **Multi-Region Support**: Switch between `2gis.ae`, `2gis.ru`, `2gis.kz`, etc., using the `-c` flag.

---

## Output Format (`./data/raw.csv`)

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

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Reinhart-py/2gis-scapper-for-b2b-data.git
   cd 2gis-scapper-for-b2b-data
