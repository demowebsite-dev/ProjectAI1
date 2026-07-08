"""Country name → ISO 3166-1 alpha-2 code mapping for Meta Ads Library.

Meta Ads Library requires an uppercase two-letter country code (e.g. ``IN``, ``US``).
This module resolves common country names, aliases, and codes to the correct value.

Usage::

    from leadfinder.crawler.meta.country_codes import resolve_country_code

    resolve_country_code("India")   # → "IN"
    resolve_country_code("in")      # → "IN"
    resolve_country_code("US")      # → "US"
    resolve_country_code("XYZ")     # → raises ValueError
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Master mapping  (all keys are lower-cased at lookup time)
# ---------------------------------------------------------------------------
_COUNTRY_MAP: dict[str, str] = {
    # Asia – South
    "india": "IN",
    "in": "IN",
    "pakistan": "PK",
    "pk": "PK",
    "bangladesh": "BD",
    "bd": "BD",
    "sri lanka": "LK",
    "lk": "LK",
    "nepal": "NP",
    "np": "NP",
    "maldives": "MV",
    "mv": "MV",
    "bhutan": "BT",
    "bt": "BT",
    # Asia – South-East
    "singapore": "SG",
    "sg": "SG",
    "malaysia": "MY",
    "my": "MY",
    "philippines": "PH",
    "ph": "PH",
    "indonesia": "ID",
    "id": "ID",
    "thailand": "TH",
    "th": "TH",
    "vietnam": "VN",
    "viet nam": "VN",
    "vn": "VN",
    "myanmar": "MM",
    "mm": "MM",
    "cambodia": "KH",
    "kh": "KH",
    # Asia – East
    "china": "CN",
    "cn": "CN",
    "japan": "JP",
    "jp": "JP",
    "south korea": "KR",
    "korea": "KR",
    "kr": "KR",
    "taiwan": "TW",
    "tw": "TW",
    "hong kong": "HK",
    "hk": "HK",
    # Middle East
    "uae": "AE",
    "united arab emirates": "AE",
    "ae": "AE",
    "saudi arabia": "SA",
    "sa": "SA",
    "kuwait": "KW",
    "kw": "KW",
    "qatar": "QA",
    "qa": "QA",
    "bahrain": "BH",
    "bh": "BH",
    "oman": "OM",
    "om": "OM",
    "israel": "IL",
    "il": "IL",
    "turkey": "TR",
    "türkiye": "TR",
    "tr": "TR",
    # Africa
    "nigeria": "NG",
    "ng": "NG",
    "south africa": "ZA",
    "za": "ZA",
    "kenya": "KE",
    "ke": "KE",
    "ghana": "GH",
    "gh": "GH",
    "ethiopia": "ET",
    "et": "ET",
    "egypt": "EG",
    "eg": "EG",
    "morocco": "MA",
    "ma": "MA",
    "tanzania": "TZ",
    "tz": "TZ",
    # Europe
    "united kingdom": "GB",
    "uk": "GB",
    "britain": "GB",
    "great britain": "GB",
    "gb": "GB",
    "germany": "DE",
    "de": "DE",
    "france": "FR",
    "fr": "FR",
    "italy": "IT",
    "it": "IT",
    "spain": "ES",
    "es": "ES",
    "netherlands": "NL",
    "nl": "NL",
    "sweden": "SE",
    "se": "SE",
    "norway": "NO",
    "no": "NO",
    "denmark": "DK",
    "dk": "DK",
    "finland": "FI",
    "fi": "FI",
    "poland": "PL",
    "pl": "PL",
    "russia": "RU",
    "ru": "RU",
    "ukraine": "UA",
    "ua": "UA",
    "portugal": "PT",
    "pt": "PT",
    "switzerland": "CH",
    "ch": "CH",
    "austria": "AT",
    "at": "AT",
    "belgium": "BE",
    "be": "BE",
    "greece": "GR",
    "gr": "GR",
    # Americas
    "united states": "US",
    "usa": "US",
    "us": "US",
    "america": "US",
    "canada": "CA",
    "ca": "CA",
    "mexico": "MX",
    "mx": "MX",
    "brazil": "BR",
    "br": "BR",
    "argentina": "AR",
    "ar": "AR",
    "colombia": "CO",
    "co": "CO",
    "chile": "CL",
    "cl": "CL",
    "peru": "PE",
    "pe": "PE",
    "venezuela": "VE",
    "ve": "VE",
    # Oceania
    "australia": "AU",
    "au": "AU",
    "new zealand": "NZ",
    "nz": "NZ",
    # Special
    "all": "ALL",
}


def resolve_country_code(country: str) -> str:
    """Resolve a country name or code to a Meta-compatible ISO alpha-2 code.

    The lookup is case-insensitive and strips surrounding whitespace.

    Args:
        country: Country name (e.g. ``"India"``) or ISO code (e.g. ``"IN"``).

    Returns:
        Uppercase ISO alpha-2 country code (e.g. ``"IN"``).

    Raises:
        ValueError: If the input cannot be resolved to a known country code.

    Examples:
        >>> resolve_country_code("India")
        'IN'
        >>> resolve_country_code("  US  ")
        'US'
        >>> resolve_country_code("united kingdom")
        'GB'
    """
    normalised = country.strip().lower()
    code = _COUNTRY_MAP.get(normalised)
    if code is None:
        known = sorted({v for v in _COUNTRY_MAP.values()})
        raise ValueError(
            f"Unknown country: {country!r}. "
            f"Use a country name (e.g. 'India') or ISO code (e.g. 'IN'). "
            f"Supported codes: {known}"
        )
    return code


def list_supported_countries() -> list[tuple[str, str]]:
    """Return a sorted list of (country_name, iso_code) pairs.

    Only the 'canonical' (longest) name for each code is returned.
    """
    seen: dict[str, str] = {}
    for name, code in _COUNTRY_MAP.items():
        if code not in seen or len(name) > len(seen[code]):
            seen[code] = name
    return sorted((name.title(), code) for code, name in seen.items())
