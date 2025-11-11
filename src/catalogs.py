import json
import os
import pandas as pd


def load_catalogs(indicators_path="data/indicators.csv", countries_path="data/countries.csv", aliases_json=None):
    ind_df = pd.read_csv(indicators_path)
    cty_df = pd.read_csv(countries_path)

    aliases = {}

    # load custom aliases if we have them
    if aliases_json and os.path.exists(aliases_json):
        with open(aliases_json, "r") as f:
            aliases.update(json.load(f))

    # build aliases from country table
    for _, row in cty_df.iterrows():
        wb3 = str(row["wb3_code"])
        for key in [str(row["name"]), str(row["iso3"]), str(row["wb2_code"]), wb3]:
            aliases[str(key).lower()] = wb3

    # add some common shortcuts
    aliases.update({
        "ksa": "SAU",
        "saudi": "SAU",
        "المملكة العربية السعودية": "SAU",
        "السعودية": "SAU",
        "usa": "USA",
        "united states": "USA",
        "us": "USA",
        "uk": "GBR",
        "united kingdom": "GBR",
        "egypt": "EGY"
    })

    return ind_df, cty_df, aliases


def normalize_country(country_text, aliases):
    if not country_text:
        raise ValueError("No country specified")

    key = country_text.strip().lower()
    key = key.replace("kingdom of saudi arabia", "saudi arabia")
    key = key.replace("united states of america", "united states")

    wb3 = aliases.get(key)
    if not wb3:
        raise ValueError(f"Could not map country '{country_text}' to a World Bank code")

    return wb3
