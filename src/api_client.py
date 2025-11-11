import time
import logging
import requests


class WorldBankClient:
    BASE_URL = "https://api.worldbank.org/v2"

    def __init__(self, timeout=10, retries=2):
        self.timeout = timeout
        self.retries = retries

    def build_url(self, country_code, indicator_code, time_param):
        return f"{self.BASE_URL}/country/{country_code}/indicator/{indicator_code}?{time_param}&format=json&per_page=2000"

    def fetch(self, url):
        last_error = None

        for attempt in range(self.retries + 1):
            try:
                response = requests.get(url, timeout=self.timeout)

                if response.status_code == 200:
                    return response.json()

                last_error = f"HTTP {response.status_code}"
                logging.warning(f"Request failed with {last_error}, attempt {attempt + 1}/{self.retries + 1}")

            except requests.Timeout:
                last_error = "Request timeout"
                logging.warning(f"Request timeout, attempt {attempt + 1}/{self.retries + 1}")

            except requests.RequestException as e:
                last_error = str(e)
                logging.warning(f"Request error: {e}, attempt {attempt + 1}/{self.retries + 1}")

            if attempt < self.retries:
                wait_time = 0.5 * (2 ** attempt)
                time.sleep(wait_time)

        raise RuntimeError(f"World Bank API error after {self.retries + 1} attempts: {last_error}")

    def fetch_indicator(self, country_code, indicator_code, time_param, requested_year=None):
        url = self.build_url(country_code, indicator_code, time_param)
        response = self.fetch(url)
        value, actual_year = self.parse_value(response, requested_year)
        return value, actual_year, url

    @staticmethod
    def parse_value(payload, requested_year=None):
        if not isinstance(payload, list) or len(payload) < 2:
            return None, None

        data = payload[1]
        if not isinstance(data, list):
            return None, None

        # try to find the exact year first
        if requested_year:
            for row in data:
                try:
                    year = int(row.get("date"))
                    if year == requested_year and row.get("value") is not None:
                        return float(row["value"]), year
                except (ValueError, TypeError):
                    continue

        # otherwise just grab the first available value
        for row in data:
            if row.get("value") is not None:
                try:
                    value = float(row["value"])
                    year = int(row.get("date"))
                    return value, year
                except (ValueError, TypeError):
                    return float(row["value"]), None

        return None, None


def format_value(value, unit, ind_id):
    if value is None:
        return "n/a"

    is_percentage = ind_id.endswith((".ZS", ".ZG")) or "%" in unit
    is_money = ind_id.endswith((".CD", ".KD")) or "US$" in unit or "dollar" in unit.lower()
    is_number = ind_id.endswith(".IN") or "number" in unit.lower()

    if is_percentage:
        return f"{value:.2f}%"

    if is_money:
        abs_val = abs(value)
        if abs_val >= 1e12:
            return f"${value/1e12:.2f}T"
        elif abs_val >= 1e9:
            return f"${value/1e9:.2f}B"
        elif abs_val >= 1e6:
            return f"${value/1e6:.2f}M"
        else:
            return f"${value:,.2f}"

    if is_number:
        abs_val = abs(value)
        if abs_val >= 1e9:
            return f"{value/1e9:.2f}B"
        elif abs_val >= 1e6:
            return f"{value/1e6:.2f}M"
        elif abs_val >= 1e3:
            return f"{value/1e3:.2f}k"

    return f"{value:,.2f}"
