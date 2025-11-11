import dspy
import logging


class QuestionToParameters(dspy.Signature):
    """Extract query parameters from a question about World Bank statistics.

    Important:
    - For 'concept': Extract only the MAIN economic/social indicator (GDP, population, unemployment, etc.)
      DO NOT include age ranges or gender in the concept field.
    - For 'demographics': Extract ONLY age and gender information separately.
    - For 'unit': Extract ONLY measurement units like USD, PPP, per capita.
    """
    question = dspy.InputField(desc="Natural language question about World Bank data")
    country = dspy.OutputField(desc="Country name only")
    concept = dspy.OutputField(desc="Main concept ONLY: GDP, population, unemployment, inflation, etc. NO age/gender")
    year = dspy.OutputField(desc="Year as a number, e.g. 2022, or 'none'")
    unit = dspy.OutputField(desc="Unit qualifiers: 'current USD', 'constant USD', 'PPP', 'per capita', 'percentage', or 'none'")
    demographics = dspy.OutputField(desc="ONLY age and gender: 'female ages 65+', 'male ages 15-24', or 'none'")


class QuestionParser:
    def __init__(self, model="llama3.2"):
        lm = dspy.LM(f'ollama_chat/{model}', api_base='http://localhost:11434', api_key='')
        dspy.configure(lm=lm)
        self.predictor = dspy.ChainOfThought(QuestionToParameters)

    def parse(self, question):
        return self._parse_with_dspy(question)

    def _parse_with_dspy(self, question):
        result = self.predictor(question=question)
        parsed = {
            'country': result.country.strip(),
            'concept': result.concept.strip(),
            'year': result.year.strip(),
            'unit': result.unit.strip() if result.unit.strip().lower() != 'none' else None,
            'demographics': result.demographics.strip() if result.demographics.strip().lower() != 'none' else None
        }

        logging.info(f"DSPy extracted: country='{parsed['country']}', concept='{parsed['concept']}', "
                     f"year='{parsed['year']}', unit='{parsed['unit']}', demographics='{parsed['demographics']}'")

        q = question.lower()
        country_text = parsed.get('country', '')
        concept = parsed.get('concept', '').lower().replace(' ', '_')

        if "cpi" in q or "consumer price index" in q:
            concept = "inflation_cpi"

        year_str = parsed.get('year', '')
        time_mode = "single"
        year = start_year = end_year = latest_n = None

        if year_str and year_str.isdigit():
            year = int(year_str)
        elif "latest" in q or "most recent" in q:
            time_mode = "latest_n"
            latest_n = 1

        unit_qualifiers = []
        unit = (parsed.get('unit') or '').lower()

        has_growth = 'growth rate' in q or 'growth' in q or 'yoy' in q

        if 'per capita' in unit or 'per capita' in q:
            unit_qualifiers.append("per_capita")
        if 'ppp' in unit or 'ppp' in q:
            unit_qualifiers.append("ppp")

        if not has_growth:
            if 'constant' in unit or 'real' in unit:
                unit_qualifiers.append("constant_usd")
            if 'current' in unit or 'nominal' in unit or 'usd' in unit:
                unit_qualifiers.append("current_usd")

        if has_growth:
            unit_qualifiers.append("growth_rate")
        elif '%' in unit or 'percent' in unit:
            unit_qualifiers.append("percent_share")
        elif ' rate' in q:
            # Don't add percent_share for concepts that are inherently rates
            if "unemployment" not in q and "inflation" not in q and "cpi" not in q:
                unit_qualifiers.append("percent_share")

        demographics = (parsed.get('demographics') or '').lower()
        sex = "total"

        # Check if concept is demographic-related (use substring matching)
        is_demographic_concept = any(key in concept for key in ["population", "unemployment", "life_expectancy"])

        if not is_demographic_concept:
            sex = "total"
        elif "total population" in q or "total pop" in q or ("population" in q and "total" in q):
            sex = "total"
            if not any(x in q for x in ["growth", "%", "percent", "share", "ratio"]):
                if "count_number" not in unit_qualifiers:
                    unit_qualifiers.append("count_number")
        elif any(word in q for word in ["female", "females", "women", "woman", "girls"]):
            sex = "female"
        elif any(word in q for word in ["male", "males", "men", "man", "boys"]) and not any(word in q for word in ["female", "females"]):
            sex = "male"
        elif "female" in demographics or "women" in demographics:
            sex = "female"
        elif ("male" in demographics or "men" in demographics) and "female" not in demographics:
            sex = "male"

        if "population" in concept and sex == "total" and not any(x in q for x in ["growth", "%", "percent", "share", "ratio"]):
            if "count_number" not in unit_qualifiers:
                unit_qualifiers.append("count_number")

        age_band = "none"
        if "65" in demographics and any(x in demographics for x in ["+", "plus", "over", "above"]):
            age_band = "65up"
        if "15-24" in demographics or "15–24" in demographics:
            age_band = "1524"

        result_slots = {
            'country_text': country_text,
            'time_mode': time_mode,
            'year': year,
            'start_year': start_year,
            'end_year': end_year,
            'latest_n': latest_n,
            'concept': concept,
            'unit_qualifiers': unit_qualifiers,
            'sex': sex,
            'age_band': age_band,
            'notes': "DSPy+Ollama"
        }

        logging.info(f"Final parsed: concept='{concept}', sex='{sex}', age_band='{age_band}', qualifiers={unit_qualifiers}")
        return result_slots


def build_time_params(slots):
    if slots["time_mode"] == "single" and slots.get("year"):
        return f"date={slots['year']}", slots["year"]

    if slots["time_mode"] == "range" and slots.get("start_year") and slots.get("end_year"):
        return f"date={slots['start_year']}:{slots['end_year']}", None

    if slots["time_mode"] == "latest_n" and slots.get("latest_n"):
        return f"mrv={slots['latest_n']}&gapfill=y", None

    return "mrv=1&gapfill=y", None
