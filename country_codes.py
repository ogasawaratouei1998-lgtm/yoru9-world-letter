"""ISO 3166-1 alpha-2 country normalization shared with the reader UI."""
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).resolve().parent / "country-catalog.json").read_text(encoding="utf-8"))

def country_code(name):
    value = str(name or "").strip().casefold()
    if not value:
        return None
    for item in catalog():
        if value == item["code"].casefold() or value == item["name"].casefold() or any(value == alias.casefold() for alias in item["aliases"]):
            return item["code"]
    return None

def country_key(name):
    return country_code(name) or str(name or "").strip()


def country_region(name):
    """Region of a recognized event/source country; unknown names stay unknown."""
    code = country_code(name)
    if code is None:
        return None
    return next((item["region"] for item in catalog() if item["code"] == code), None)
