def __init__(self, config: Namespace) -> None:
        country_code = getattr(config, "country", "ae")
        self.search_query: str = build_search_query(
            city_name=config.city_name,
            query=config.query_string,
            country_tld=country_code,
        )
        self.output_dir: str = config.output_path
