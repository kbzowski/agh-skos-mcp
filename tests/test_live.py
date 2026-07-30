"""Contract tests against the live directory - run with `pytest -m network`.

Fixtures deliberately use the maintainer's own record so the suite does not
depend on unrelated people's data staying put.
"""

import pytest

from agh_skos_mcp import skos

pytestmark = pytest.mark.network

SLUG = "krzysztof-bzowski-7674"
UNIT = "Katedra Informatyki Stosowanej i Modelowania"


def test_every_dictionary_endpoint_answers() -> None:
    for field in skos.DICT_FIELDS:
        assert skos.options(field), field


def test_labels_resolve_to_the_ids_the_form_uses() -> None:
    assert skos.resolve("id_status", "Emeryt") == "3"
    assert skos.resolve("grupa", "adiunkci") == "2"


def test_search_by_unit_returns_many_hits() -> None:
    results = skos.search(jednostka=UNIT)
    assert results["total"] > 1
    assert results["person"] is None
    assert any(hit["name"] == "Bzowski Krzysztof" for hit in results["results"])


def test_a_single_hit_redirects_to_the_profile_and_is_still_reported() -> None:
    results = skos.search(nazwisko="Bzowski")
    assert results["total"] == 1
    assert results["person"] is not None
    assert results["person"]["emails"] == ["kbzowski@agh.edu.pl"]


def test_search_combines_text_and_dictionary_filters() -> None:
    results = skos.search(nazwisko="Bzowski", jednostka=UNIT, grupa="adiunkci")
    assert results["total"] == 1


def test_get_person() -> None:
    person = skos.get_person(SLUG)
    assert person["name"] == "Krzysztof Bzowski"
    assert person["title"] == "dr inż."
    assert person["emails"] == ["kbzowski@agh.edu.pl"]
    workplace = person["workplaces"][0]
    assert workplace["job"] == "adiunkt"
    assert workplace["units"][-1] == UNIT


def test_get_person_rejects_an_unknown_slug() -> None:
    with pytest.raises(skos.SkosError):
        skos.get_person("nie-ma-takiej-osoby-999999")
