import csv
import math
import os
import sys
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://2gis.ae/",
}
API_KEYS = ["ruxbgf7743", "rurbbn3446", "rurtad3286"]

def get_region_id(city_name: str, key: str) -> str | None:
    url = "https://catalog.api.2gis.com/2.0/region/search"
    params = {"q": city_name, "key": key}
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=10).json()
        items = res.get("result", {}).get("items", [])
        if items:
            return items[0]["id"]
    except Exception:
        pass
    return None

def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "Dubai"
    query = sys.argv[2] if len(sys.argv) > 2 else "Supermarkets"
    output_file = "./data/raw.csv"
    os.makedirs("./data", exist_ok=True)

    key = API_KEYS[0]
    region_id = get_region_id(city, key)

    print(f"Searching for '{query}' in '{city}' (Region ID: {region_id or 'Global'})...")

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "phone", "address"])

    page = 1
    page_size = 50
    total_items = None
    total_scraped = 0

    with open(output_file, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        while True:
            url = "https://catalog.api.2gis.com/3.0/items"
            params = {
                "q": f"{city} {query}" if not region_id else query,
                "page": page,
                "page_size": page_size,
                "fields": "items.contact_groups,items.address_name",
                "key": key,
                "locale": "en_AE",
            }
            if region_id:
                params["region_id"] = region_id

            try:
                res = requests.get(url, params=params, headers=HEADERS, timeout=15).json()
            except Exception as e:
                print(f"Network error on page {page}: {e}")
                break

            result = res.get("result", {})
            items = result.get("items", [])

            if total_items is None:
                total_items = result.get("total", 0)
                total_pages = math.ceil(total_items / page_size) if total_items else 0
                print(f"Found {total_items} listings (~{total_pages} pages to fetch).")

            if not items:
                break

            for item in items:
                title = item.get("name") or "null"
                address = item.get("address_name") or "null"

                phones = []
                for group in item.get("contact_groups", []):
                    for contact in group.get("contacts", []):
                        if contact.get("type") == "phone":
                            phone_val = contact.get("text") or contact.get("value")
                            if phone_val:
                                phones.append(str(phone_val).strip())

                phone_str = ", ".join(phones) if phones else "null"
                writer.writerow([title, phone_str, address])
                total_scraped += 1

            print(f"Page {page} scraped ({len(items)} items, {total_scraped}/{total_items} total)")
            page += 1
            if page_size * (page - 1) >= total_items:
                break

    print(f"Done! Scraped {total_scraped} records into {output_file}")

if __name__ == '__main__':
    main()
