import urllib.parse


def build_search_query(city_name: str, query: str | list[str], country_tld: str = "ae") -> str:
    # If passed as a list from nargs='+', join with a space
    if isinstance(query, list):
        query_text = " ".join(query)
    else:
        query_text = str(query)

    # Clean and encode spaces and special characters like \, &, /
    clean_query = urllib.parse.quote(query_text.strip())
    clean_city = urllib.parse.quote(city_name.strip().lower())
    tld = country_tld.strip().lstrip(".")

    return f"https://2gis.{tld}/{clean_city}/search/{clean_query}?m"
