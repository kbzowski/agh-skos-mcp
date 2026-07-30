"""Offline unit tests - no network access."""

import json

import pytest

from agh_skos_mcp import skos


def test_deobfuscate_email() -> None:
    blob = '>a/<lp.ude.hga#ikswozbk>"lp.ude.hga#ikswozbk:otliam"=ferh a<'
    assert skos.deobfuscate_email(blob) == "kbzowski@agh.edu.pl"


def test_deobfuscate_email_leaves_a_plain_address_alone() -> None:
    """Reversing an unobfuscated address would yield a plausible wrong one."""
    assert skos.deobfuscate_email("kbzowski@agh.edu.pl") == "kbzowski@agh.edu.pl"


def test_deobfuscate_email_rejects_junk() -> None:
    with pytest.raises(skos.SkosError):
        skos.deobfuscate_email("nie e-mail")


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


def test_person_url_refuses_a_foreign_host() -> None:
    with pytest.raises(ValueError, match="Refusing to fetch"):
        skos.person_url("http://169.254.169.254/latest/meta-data/")


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


def _serve(monkeypatch: pytest.MonkeyPatch, page_props: object, final_url: str) -> None:
    """Pretend the site returned a page carrying these Next.js props."""
    body = (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps({"props": {"pageProps": page_props}})
        + "</script>"
    )
    monkeypatch.setattr(skos, "_fetch", lambda url: (body, final_url))


def test_search_parses_a_result_list(monkeypatch: pytest.MonkeyPatch) -> None:
    items = [
        {
            "name": f"Testowy {index}",
            "title": {"pl": "dr"},
            "url": f"/osoba/testowy-{index}.html",
            "status": [1],
            "workplaces": [{"workplace": {"pl": "Katedra Testów"}}],
        }
        for index in range(3)
    ]
    _serve(monkeypatch, {"data": {"items": items}}, f"{skos.BASE}/search?nazwisko=Testowy")

    results = skos.search(nazwisko="Testowy", limit=2)

    assert results["total"] == 3
    assert results["returned"] == 2
    assert results["person"] is None
    assert results["results"][0]["units"] == ["Katedra Testów"]


def test_search_follows_the_single_hit_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = f"{skos.BASE}/osoba/krzysztof-bzowski-7674.html"
    _serve(monkeypatch, {"data": {"lastname": "Bzowski", "name1": "Krzysztof"}}, profile)

    results = skos.search(nazwisko="Bzowski")

    assert results["total"] == 1
    assert results["person"] is not None
    assert results["person"]["name"] == "Krzysztof Bzowski"
    assert results["results"][0]["url"] == profile


def test_search_reports_a_page_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _serve(monkeypatch, {"error": 500}, f"{skos.BASE}/search?nazwisko=X")

    with pytest.raises(skos.SkosError, match="500"):
        skos.search(nazwisko="X")


def test_limit_below_one_still_returns_a_result(monkeypatch: pytest.MonkeyPatch) -> None:
    items = [{"name": "Testowy", "url": "/osoba/testowy-1.html"}]
    _serve(monkeypatch, {"data": {"items": items}}, f"{skos.BASE}/search?nazwisko=Testowy")

    assert skos.search(nazwisko="Testowy", limit=-1)["returned"] == 1


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
