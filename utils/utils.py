def build_search_query(
    city_name: str, query: str, country_tld: str = "ae", page: int = 1
) -> str:
    tld = country_tld.strip().lstrip(".")
    base_url = f"https://2gis.{tld}/{city_name.lower()}/search/{query.title()}"
    if page > 1:
        return f"{base_url}/page/{page}?m"
    return f"{base_url}?m"
