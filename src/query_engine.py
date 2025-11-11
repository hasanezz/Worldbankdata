from .catalogs import load_catalogs, normalize_country
from .parser import QuestionParser, build_time_params
from .indexer import IndicatorIndex
from .resolver import IndicatorResolver, build_query_terms
from .api_client import WorldBankClient, format_value


class QueryEngine:
    def __init__(self, indicators_path="data/indicators.csv", countries_path="data/countries.csv",
                 aliases_json=None, index_path=None, dspy_model="llama3.2"):
        self.ind_df, self.cty_df, self.aliases = load_catalogs(indicators_path, countries_path, aliases_json)
        self.parser = QuestionParser(model=dspy_model)

        self.index = IndicatorIndex()
        if index_path:
            self.index.load(index_path)
        else:
            self.index.build(self.ind_df)

        self.resolver = IndicatorResolver(self.ind_df)
        self.api_client = WorldBankClient()

    def answer(self, question):
        slots = self.parser.parse(question)
        country_code = normalize_country(slots.get("country_text", ""), self.aliases)
        time_param, requested_year = build_time_params(slots)

        query_text = build_query_terms(slots)
        search_results = self.index.search(query_text, top_k=50)

        ind_code, ind_name, ind_unit, confidence, notes = self.resolver.resolve(slots, search_results)

        value, actual_year, api_url = self.api_client.fetch_indicator(
            country_code, ind_code, time_param, requested_year
        )

        value_str = format_value(value, ind_unit, ind_code)

        result = {
            "question": question,
            "country": country_code,
            "indicator_code": ind_code,
            "indicator_name": ind_name,
            "unit": ind_unit,
            "value": value_str,
            "year_used": actual_year,
            "api_url": api_url,
            "confidence_margin": round(confidence, 4),
            "resolver_note": notes
        }

        if requested_year and actual_year != requested_year:
            result["note"] = f"No data for {requested_year}; showing {actual_year} (nearest/latest available)."

        return result
