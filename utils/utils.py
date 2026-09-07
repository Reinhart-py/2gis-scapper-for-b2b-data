def build_search_query(city_name: str, query: str, country_tld: str = "ae") -> str:
    tld = country_tld.strip().lstrip(".")
    return f"https://2gis.{tld}/{city_name.lower()}/search/{query.title()}?m"
