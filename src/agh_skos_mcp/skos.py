"""Client for skos.agh.edu.pl - the AGH staff directory."""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Any, Final, Literal, TypedDict, cast

BASE: Final = "https://skos.agh.edu.pl"
USER_AGENT: Final = "agh-skos-mcp/0.1 (+https://github.com/kbzowski/agh-skos-mcp)"
TIMEOUT: Final = 30

_NEXT_DATA: Final = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)
_TAGS: Final = re.compile(r"<[^>]+>")

DictField = Literal[
    "tytul", "id_status", "grupa", "stanowisko", "funkcja", "jednostka", "pawilon", "cialo"
]

#: Search form field -> id of the matching `/a/select` dictionary endpoint.
DICT_FIELDS: Final[dict[DictField, str]] = {
    "tytul": "titles",
    "id_status": "statuses",
    "grupa": "groups",
    "stanowisko": "jobs",
    "funkcja": "functions",
    "jednostka": "units",
    "pawilon": "buildings",
    "cialo": "collegials",
}

TEXT_FIELDS: Final = ("nazwisko", "imie", "email", "pokoj", "telefon")


class SkosError(RuntimeError):
    """The directory returned something we cannot use."""


class Option(TypedDict):
    value: str
    label: str


class Workplace(TypedDict):
    units: list[str]
    job: str | None
    group: str | None
    function: str | None
    status: str | None
    office: str | None
    phones: list[str]


class Person(TypedDict):
    id: int | None
    name: str
    title: str | None
    emails: list[str]
    mobile_phones: list[str]
    www: list[str]
    workplaces: list[Workplace]
    collegial: list[str]
    annotations: str | None
    url: str


class SearchHit(TypedDict):
    name: str | None
    title: str | None
    url: str | None
    status: list[int]
    units: list[str]


class SearchResults(TypedDict):
    total: int
    returned: int
    query: str
    results: list[SearchHit]
    #: Filled in only when the query matched exactly one person, because the
    #: site then redirects straight to the profile and hands us the full record.
    person: Person | None


def _fetch(url: str) -> tuple[str, str]:
    """Return the response body and the final URL after any redirects."""
    if not url.startswith(f"{BASE}/"):
        raise ValueError(f"Refusing to fetch {url!r}: not a {BASE} address")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            charset = response.headers.get_content_charset("utf-8")
            return response.read().decode(charset), response.geturl()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SkosError(f"Request to {url} failed: {exc}") from exc


def _page_props(url: str) -> tuple[dict[str, Any], str]:
    """Extract the Next.js page props embedded in a rendered SkOs page."""
    body, final_url = _fetch(url)
    match = _NEXT_DATA.search(body)
    if match is None:
        raise SkosError(f"__NEXT_DATA__ not found at {final_url}")
    props = json.loads(match.group(1))["props"]["pageProps"]
    if props.get("error"):
        raise SkosError(f"SkOs returned error {props['error']} for {final_url}")
    return cast("dict[str, Any]", props), final_url


def deobfuscate_email(blob: str) -> str:
    """Undo the site's obfuscation: a reversed <a> tag with '#' for '@'.

    Reversing an address the site stopped obfuscating would silently yield a
    plausible but wrong one, so the marker is checked and the result verified.
    """
    text = _TAGS.sub("", blob[::-1] if "#" in blob else blob)
    email = html.unescape(text).replace("#", "@").strip()
    if "@" not in email:
        raise SkosError(f"Cannot decode an e-mail address from {blob!r}")
    return email


def person_url(reference: str) -> str:
    """Normalise a profile slug, path or URL into an absolute profile URL."""
    reference = reference.strip()
    if reference.startswith(("http://", "https://")):
        if not reference.startswith(f"{BASE}/"):
            raise ValueError(f"Refusing to fetch {reference!r}: not a {BASE} URL")
        return reference
    if not reference.startswith("/"):
        reference = f"/osoba/{reference}"
    if not reference.endswith(".html"):
        reference += ".html"
    return BASE + reference


@lru_cache(maxsize=len(DICT_FIELDS))
def options(field: DictField) -> list[Option]:
    """Allowed values of a dictionary filter, as served to the search form."""
    if field not in DICT_FIELDS:
        raise ValueError(f"Unknown field {field!r}; expected one of {tuple(DICT_FIELDS)}")
    body, _ = _fetch(f"{BASE}/a/select?id={DICT_FIELDS[field]}")
    items: list[dict[str, Any]] = json.loads(body)["items"]
    result: list[Option] = []
    for item in items:
        title = item.get("title")
        label = title if isinstance(title, str) else (title or {}).get("pl")
        result.append({"value": str(item.get("id", "")), "label": (label or "").strip()})
    return result


def resolve(field: DictField, value: str) -> str:
    """Turn a dictionary filter value (id or Polish label) into its id."""
    if value.lstrip("-").isdigit():
        return value
    needle = value.casefold()
    available = options(field)
    exact = [option for option in available if option["label"].casefold() == needle]
    hits = exact or [option for option in available if needle in option["label"].casefold()]
    if not hits:
        raise ValueError(f"No option matching {value!r} in {field}")
    if len(hits) > 1:
        candidates = ", ".join(repr(option["label"]) for option in hits[:10])
        raise ValueError(f"Ambiguous {field}={value!r}; candidates: {candidates}")
    return hits[0]["value"]


def _polish_names(entries: list[dict[str, Any]] | None, key: str) -> list[str]:
    """Collect the Polish display names of nested dictionary entries, dropping blanks."""
    names = ((entry.get(key) or {}).get("pl") for entry in entries or [] if entry)
    return [name for name in names if name]


def _parse_workplace(raw: dict[str, Any]) -> Workplace:
    office = raw.get("office") or {}
    location = " ".join(
        str(part)
        for part in (office.get("building"), office.get("floor"), office.get("room"))
        if part
    )
    return {
        "units": _polish_names(raw.get("unit"), "displayName"),
        "job": (raw.get("job") or {}).get("pl"),
        "group": (raw.get("group") or {}).get("pl"),
        "function": (raw.get("function") or {}).get("pl") if raw.get("function") else None,
        "status": (raw.get("status") or {}).get("pl"),
        "office": location or None,
        "phones": [
            "+" + " ".join(filter(None, (phone.get("countryCode"), phone.get("phoneNumber"))))
            for phone in raw.get("phoneDetails") or []
        ],
    }


def parse_person(raw: dict[str, Any], url: str) -> Person:
    names = (raw.get("name1"), raw.get("name2"), raw.get("lastname"))
    return {
        "id": raw.get("id"),
        "name": " ".join(part for part in names if part),
        "title": ((raw.get("title") or {}).get("displayName") or {}).get("pl"),
        "emails": [deobfuscate_email(email) for email in raw.get("emails") or []],
        "mobile_phones": raw.get("mobilePhone") or [],
        "www": raw.get("www") or [],
        "workplaces": [_parse_workplace(workplace) for workplace in raw.get("workplaces") or []],
        "collegial": _polish_names(raw.get("collegial"), "displayName"),
        "annotations": raw.get("annotations") or None,
        "url": url,
    }


def _parse_hit(raw: dict[str, Any]) -> SearchHit:
    return {
        "name": raw.get("name"),
        "title": (raw.get("title") or {}).get("pl"),
        "url": raw.get("url"),
        "status": raw.get("status") or [],
        "units": _polish_names(raw.get("workplaces"), "workplace"),
    }


def search(*, limit: int = 50, **filters: str) -> SearchResults:
    """Run the advanced search. Text filters are passed through verbatim,
    dictionary filters are resolved from labels to ids."""
    params = {field: filters.get(field, "") for field in TEXT_FIELDS}
    for field in DICT_FIELDS:
        value = filters.get(field, "")
        params[field] = resolve(field, value) if value else "0"

    if not any(params[field] for field in TEXT_FIELDS) and all(
        params[field] == "0" for field in DICT_FIELDS
    ):
        raise ValueError("Provide at least one filter")

    url = f"{BASE}/search/?" + urllib.parse.urlencode(params)
    props, final_url = _page_props(url)
    data = props.get("data") or {}

    # A single match makes the site redirect to the profile instead of listing it.
    # Match on the data shape too, so a change to that jump fails loudly rather
    # than silently reporting "nobody found".
    if final_url.startswith(f"{BASE}/osoba/") or data.get("lastname"):
        person = parse_person(data, final_url)
        hit: SearchHit = {
            "name": person["name"],
            "title": person["title"],
            "url": final_url,
            "status": [],
            "units": [
                workplace["units"][-1] for workplace in person["workplaces"] if workplace["units"]
            ],
        }
        return {"total": 1, "returned": 1, "query": url, "results": [hit], "person": person}

    items: list[dict[str, Any]] = data.get("items") or []
    results = [_parse_hit(item) for item in items[: max(1, limit)]]
    return {
        "total": len(items),
        "returned": len(results),
        "query": url,
        "results": results,
        "person": None,
    }


def get_person(reference: str) -> Person:
    """Fetch a full profile by slug, path or URL."""
    props, final_url = _page_props(person_url(reference))
    data = props.get("data")
    if not data:
        raise SkosError(f"No person data for {reference!r}")
    return parse_person(data, final_url)
