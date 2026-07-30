"""MCP server exposing the AGH staff directory as tools."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from agh_skos_mcp import __version__, skos
from agh_skos_mcp.skos import Option, Person, SearchResults

mcp = MCPServer(
    "agh-skos",
    version=__version__,
    instructions=(
        "Search AGH University staff in the SkOs directory (skos.agh.edu.pl). "
        "Start with search_people, then get_person for full contact data."
    ),
)


@mcp.tool()
def list_filter_options(field: str, contains: str = "") -> list[Option]:
    """List allowed values for a dictionary filter of search_people.

    field: one of tytul, id_status, grupa, stanowisko, funkcja, jednostka,
           pawilon, cialo.
    contains: optional case-insensitive substring to narrow the list.
    """
    if field not in skos.DICT_FIELDS:
        raise ValueError(f"Unknown field {field!r}; expected one of {tuple(skos.DICT_FIELDS)}")
    available = skos.options(field)
    if not contains:
        return available
    needle = contains.casefold()
    return [option for option in available if needle in option["label"].casefold()]


@mcp.tool()
def search_people(
    nazwisko: str = "",
    imie: str = "",
    email: str = "",
    pokoj: str = "",
    telefon: str = "",
    tytul: str = "",
    id_status: str = "",
    grupa: str = "",
    stanowisko: str = "",
    funkcja: str = "",
    jednostka: str = "",
    pawilon: str = "",
    cialo: str = "",
    limit: int = 50,
) -> SearchResults:
    """Search AGH staff in the SkOs directory (skos.agh.edu.pl advanced search).

    Text filters (nazwisko, imie, email, pokoj, telefon) are case-insensitive
    prefix matches - no wildcards. Dictionary filters (tytul, id_status, grupa,
    stanowisko, funkcja, jednostka, pawilon, cialo) accept either the numeric id
    or the Polish label - use list_filter_options to browse them.

    Returns matching people with their title, unit and profile url; pass that
    url to get_person for contact data. When exactly one person matches, the
    full profile is already included in the "person" field.
    """
    return skos.search(
        limit=limit,
        nazwisko=nazwisko,
        imie=imie,
        email=email,
        pokoj=pokoj,
        telefon=telefon,
        tytul=tytul,
        id_status=id_status,
        grupa=grupa,
        stanowisko=stanowisko,
        funkcja=funkcja,
        jednostka=jednostka,
        pawilon=pawilon,
        cialo=cialo,
    )


@mcp.tool()
def get_person(person: str) -> Person:
    """Fetch a full SkOs profile: units, position, room, phones, email, www.

    person: profile url or slug as returned by search_people, e.g.
    "/osoba/krzysztof-bzowski-7674.html" or "krzysztof-bzowski-7674".
    """
    return skos.get_person(person)


__all__ = ["mcp"]
