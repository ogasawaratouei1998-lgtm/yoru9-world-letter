"""Normalize the app's 196 reporting locations to ISO 3166-1 alpha-2 codes.

The editorial target is 193 UN members + Holy See + Palestine + Taiwan.
This is a reporting-geography convention, not a claim of state recognition.
Source/publisher markets never count as an event's country.
"""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).resolve().parent / "country-catalog.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _country_index():
    result={}
    for item in catalog():
        for label in (item["code"],item["name"],*item["aliases"]):
            normalized=str(label).strip().casefold()
            previous=result.setdefault(normalized,item["code"])
            if previous!=item["code"]:
                raise ValueError("country alias shared by multiple locations")
    return result


def country_code(name):
    """Recognize one complete country label; never guess using substrings."""
    value=str(name or "").strip().casefold()
    return _country_index().get(value) if value else None


def country_codes(name):
    """Honor explicitly named cross-border events in older published editions.

    Full-match BEFORE splitting: e.g. アンティグア・バーブーダ is one country,
    while イギリス・アメリカ refers to two. Unknown pieces stay unrecognized.
    """
    if isinstance(name,(list,tuple)):
        values=[country_code(x) for x in name]
        return list(dict.fromkeys(values)) if values and all(values) else []
    single=country_code(name)
    if single:
        return [single]
    value=str(name or "").strip()
    for delimiter in ("・","／","/","、"," and "):
        if delimiter in value:
            parts=[part.strip() for part in value.split(delimiter)]
            codes=[country_code(part) for part in parts]
            if len(parts)>1 and all(codes):
                return list(dict.fromkeys(codes))
    return []


def country_key(name):
    return country_code(name) or str(name or "").strip()


def country_region(name):
    """Region of one recognized event/source country; unknown stays unknown."""
    code=country_code(name)
    if code is None:
        return None
    return next((item["region"] for item in catalog() if item["code"]==code),None)
