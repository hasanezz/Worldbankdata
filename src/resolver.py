import pandas as pd


def is_percent(ind_id, name, unit):
    return ind_id.endswith(".ZS") or "%)" in name or "%" in unit or "percent" in unit.lower()


def is_growth(ind_id, name):
    return ind_id.endswith(".ZG") or "growth (annual %)" in name.lower()


def is_count(ind_id, unit):
    if ind_id.endswith(".ZS") or ind_id.endswith(".ZG"):
        return False
    return ind_id.endswith(".IN") or "number" in unit.lower() or unit.strip() == ""


def is_ppp(ind_id, name):
    return ".PP" in ind_id or "ppp" in name.lower()


def is_constant(ind_id, name):
    return ind_id.endswith(".KD") or "constant" in name.lower()


def is_current_usd(ind_id, name, unit):
    return ind_id.endswith(".CD") or "current us$" in name.lower() or "current" in unit.lower()


def has_sex(ind_id, sex):
    if sex == "female":
        return ".FE." in ind_id or ind_id.endswith(".FE.IN") or ind_id.endswith(".FE.ZS") or ind_id.endswith(".FE")
    if sex == "male":
        return ".MA." in ind_id or ind_id.endswith(".MA.IN") or ind_id.endswith(".MA.ZS") or ind_id.endswith(".MA")
    if sex == "total":
        return not (".FE." in ind_id or ".MA." in ind_id)
    return True


def has_age(ind_id, age_band):
    if age_band == "none":
        return True

    age_codes = {"65up": "65UP", "1524": "1524", "0t04": "0T04", "1564": "1564"}
    code = age_codes.get(age_band)
    if code:
        return code in ind_id

    return True


def build_query_terms(slots):
    import re

    bits = []

    concept = (slots.get("concept") or "").replace("_", " ").replace("\n", " ").replace("\r", " ")

    # Clean concept - remove age/demographic info that's captured separately
    # Remove patterns like: "female ages 65+", "male ages 15-24", "ages 65 and above"
    concept = re.sub(r'\b(fe)?male\s+(ages?|age)\s+[\d\-\+\sandabove]+', '', concept, flags=re.IGNORECASE)
    concept = re.sub(r'\b(fe)?male', '', concept, flags=re.IGNORECASE)
    concept = re.sub(r'\bages?\s+[\d\-\+\sandabove]+', '', concept, flags=re.IGNORECASE)
    # Remove age ranges in parentheses: (ages 65+), (age 15-24)
    concept = re.sub(r'\s*\(ages?\s+[\d\-\+\sandabove]+\)', '', concept, flags=re.IGNORECASE)
    # Remove gender info in parentheses: (male), (female)
    concept = re.sub(r'\s*\(.*?(male|female).*?\)', '', concept, flags=re.IGNORECASE)
    # Collapse multiple spaces
    concept = re.sub(r'\s+', ' ', concept).strip()

    if concept and concept != "unknown":
        bits.append(concept)

    uq = set(slots.get("unit_qualifiers") or [])

    # Add meaningful qualifiers, skip redundant ones
    for qualifier in uq:
        if qualifier == "percent_share":
            bits.append("percent")
        elif qualifier == "growth_rate":
            bits.append("growth")
        elif qualifier == "per_capita":
            bits.append("per capita")
        elif qualifier == "ppp":
            bits.append("ppp")
        elif qualifier == "current_usd":
            bits.append("current")
        elif qualifier == "constant_usd":
            bits.append("constant")

    sex = slots.get("sex")
    if sex and sex != "total":
        bits.append(sex)

    age_band = slots.get("age_band")
    if age_band and age_band != "none":
        age_map = {"65up": "65+", "1524": "15-24", "0t04": "0-4", "1564": "15-64"}
        age_str = age_map.get(age_band, age_band)
        bits.append(age_str)

    query = " ".join(bits).strip()
    return query or concept


class IndicatorResolver:
    def __init__(self, ind_df):
        self.ind_df = ind_df
        self.id2row = {row["id"]: row for _, row in ind_df.iterrows()}

    def resolve(self, slots, search_results):
        # build candidate list
        candidates = []
        for ind_id, semantic_score in search_results:
            row = self.id2row.get(ind_id)
            if row is None:
                continue

            candidates.append({
                'id': row["id"],
                'name': row["name"],
                'unit': str(row.get("unit", "")),
                'topics': str(row.get("topics", "")),
                'sourceNote': str(row.get("sourceNote", "")),
                'source': str(row.get("source", "")),
                'semantic': float(semantic_score)
            })

        # apply hard constraints
        filtered = self._apply_constraints(candidates, slots)

        if not filtered:
            query = build_query_terms(slots)
            raise ValueError(f"No suitable indicator after constraints for query='{query}'")

        # score and rank
        scored = self._score_candidates(filtered, slots)

        # return best match
        best = scored[0]
        second_score = scored[1]["score"] if len(scored) > 1 else 0.0
        confidence_margin = max(0.0, best["score"] - second_score)

        query = build_query_terms(slots)
        notes = f"query='{query}', semantic={best['semantic']:.3f}"

        return best["id"], best["name"], best["unit"], confidence_margin, notes

    def _apply_constraints(self, candidates, slots):
        uq = set(slots.get("unit_qualifiers") or [])
        sex = slots.get("sex", "total")
        age = slots.get("age_band", "none")

        filtered = []
        for cand in candidates:
            if "ppp" in uq and not is_ppp(cand["id"], cand["name"]):
                continue

            if "growth_rate" in uq and not is_growth(cand["id"], cand["name"]):
                continue

            if "percent_share" in uq:
                if not is_percent(cand["id"], cand["name"], cand["unit"]):
                    if "rate" not in cand["name"].lower():
                        continue

            if not has_sex(cand["id"], sex):
                continue

            if not has_age(cand["id"], age):
                continue

            filtered.append(cand)

        return filtered

    def _score_candidates(self, candidates, slots):
        uq = set(slots.get("unit_qualifiers") or [])
        sex = slots.get("sex", "total")
        age = slots.get("age_band", "none")
        concept = slots.get("concept", "").lower()

        for cand in candidates:
            # unit qualifier matching
            unit_match = 0.0
            if "ppp" in uq and is_ppp(cand["id"], cand["name"]):
                unit_match += 1.0
            if "growth_rate" in uq and is_growth(cand["id"], cand["name"]):
                unit_match += 1.0
            if "percent_share" in uq and is_percent(cand["id"], cand["name"], cand["unit"]):
                unit_match += 1.0
            if "count_number" in uq and is_count(cand["id"], cand["unit"]):
                unit_match += 1.0
            if "constant_usd" in uq and is_constant(cand["id"], cand["name"]):
                unit_match += 1.0
            if "current_usd" in uq and is_current_usd(cand["id"], cand["name"], cand["unit"]):
                unit_match += 1.0
            if "per_capita" in uq and (".PC" in cand["id"] or "per capita" in cand["name"].lower()):
                unit_match += 1.0

            # demographics matching
            demo_match = 0.0
            if has_sex(cand["id"], sex):
                demo_match += 1.0
            if has_age(cand["id"], age):
                demo_match += 1.0

            # concept-specific boosts
            prior = 0.0
            if concept in ("inflation", "inflation_cpi"):
                if "consumer prices (annual %)" in cand["name"].lower() or cand["id"] == "FP.CPI.TOTL.ZG":
                    prior += 1.0
            if concept == "gdp":
                if cand["id"].startswith("NY.GDP.MKTP"):
                    prior += 1.0
            if concept == "population":
                if cand["id"] == "SP.POP.TOTL" and sex == "total":
                    prior += 2.0
                elif cand["id"].startswith("SP.POP"):
                    prior += 0.8

            # combined score
            cand["score"] = (
                0.45 * cand["semantic"] +
                0.25 * unit_match +
                0.15 * demo_match +
                0.10 * prior +
                0.05 * 0.0
            )

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates
