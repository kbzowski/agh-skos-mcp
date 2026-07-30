"""Offline unit tests - no network access."""

import pytest

from agh_skos_mcp import skos


def test_deobfuscate_email() -> None:
    blob = '>a/<lp.ude.hga#ikswozbk>"lp.ude.hga#ikswozbk:otliam"=ferh a<'
    assert skos.deobfuscate_email(blob) == "kbzowski@agh.edu.pl"


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("krzysztof-bzowski-7674", "https://skos.agh.edu.pl/osoba/krzysztof-bzowski-7674.html"),
        (
            "/osoba/krzysztof-bzowski-7674.html",
            "https://skos.agh.edu.pl/osoba/krzysztof-bzowski-7674.html",
        ),
        ("https://skos.agh.edu.pl/osoba/x-1.html", "https://skos.agh.edu.pl/osoba/x-1.html"),
    ],
)
def test_person_url(reference: str, expected: str) -> None:
    assert skos.person_url(reference) == expected


def test_resolve_passes_ids_through_without_network() -> None:
    assert skos.resolve("tytul", "12") == "12"
    assert skos.resolve("cialo", "-473") == "-473"


def test_resolve_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        skos,
        "options",
        lambda field: [
            {"value": "1", "label": "adiunkci"},
            {"value": "2", "label": "starsi wykładowcy"},
            {"value": "3", "label": "wykładowcy"},
        ],
    )
    assert skos.resolve("grupa", "adiunkci") == "1"
    assert skos.resolve("grupa", "ADIUNKCI") == "1"
    # An exact match wins over the substring that also hits "starsi wykładowcy".
    assert skos.resolve("grupa", "wykładowcy") == "3"

    with pytest.raises(ValueError, match="Ambiguous"):
        skos.resolve("grupa", "wykład")
    with pytest.raises(ValueError, match="No option matching"):
        skos.resolve("grupa", "nie ma takiej")


def test_search_rejects_an_empty_query() -> None:
    with pytest.raises(ValueError, match="at least one filter"):
        skos.search()


def test_parse_person_maps_the_public_fields() -> None:
    raw = {
        "id": 7674,
        "name1": "Krzysztof",
        "name2": None,
        "lastname": "Bzowski",
        "title": {"displayName": {"pl": "dr inż."}},
        "emails": ['>a/<lp.ude.hga#ikswozbk>"lp.ude.hga#ikswozbk:otliam"=ferh a<'],
        "www": ["http://home.agh.edu.pl/kbzowski"],
        "workplaces": [
            {
                "office": {"building": "B-5", "floor": "VI p.", "room": "pok. 605"},
                "group": {"pl": "adiunkci"},
                "job": {"pl": "adiunkt"},
                "status": {"pl": "Pracownik"},
                "unit": [{"displayName": {"pl": "Katedra Informatyki Stosowanej i Modelowania"}}],
                "phoneDetails": [{"countryCode": "48", "phoneNumber": "12 617 26 15"}],
            }
        ],
    }

    person = skos.parse_person(raw, "https://skos.agh.edu.pl/osoba/krzysztof-bzowski-7674.html")

    assert person["name"] == "Krzysztof Bzowski"
    assert person["emails"] == ["kbzowski@agh.edu.pl"]
    assert person["mobile_phones"] == []
    workplace = person["workplaces"][0]
    assert workplace["office"] == "B-5 VI p. pok. 605"
    assert workplace["phones"] == ["+48 12 617 26 15"]
    assert workplace["function"] is None
