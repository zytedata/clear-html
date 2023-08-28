from pathlib import Path

import pytest
from lxml.html import fromstring

from clear_html import clean_node
from clear_html.body_annotations import BodyAnnotation, BodyAnnotations
from clear_html.clean import cleaned_node_to_html, cleaned_node_to_text
from clear_html.formatted_text import clean_doc
from clear_html.html_embeddings import integrate_embeddings

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "body_formatting_annotations.json"


def test_load_and_save(tmpdir):
    path = tmpdir / "ann.json"
    expected = BodyAnnotations()
    expected["two"] = BodyAnnotation(
        expected_html="expected2", raw_html="raw2", url="url"
    )
    expected["one"] = BodyAnnotation(
        raw_html="raw", expected_html="expected", url="url"
    )
    expected.save(path)
    actual = BodyAnnotations.load(path)
    assert expected == actual


@pytest.mark.parametrize(
    ("fixture_id", "item"),
    BodyAnnotations.load(FIXTURES_PATH).items(),
    ids=lambda fixture_id: fixture_id if type(fixture_id) is str else "",
)
def test_body_formatting(fixture_id: str, item: BodyAnnotation):
    """Checks that body formatting as html is right"""
    node = fromstring(item.raw_html, base_url=item.url)
    nodes_whitelist = integrate_embeddings(node)
    node = clean_doc(node, item.url, nodes_whitelist)
    formatted_body = cleaned_node_to_html(node)
    assert formatted_body == item.expected_html


@pytest.mark.parametrize(
    ("fixture_id", "item"),
    BodyAnnotations.load(FIXTURES_PATH).items(),
    ids=lambda fixture_id: fixture_id if type(fixture_id) is str else "",
)
@pytest.mark.xfail  # Fails because https://github.com/TeamHG-Memex/html-text/issues/16
def test_body_as_text_same_after_cleaning(fixture_id: str, item: BodyAnnotation):
    """
    Checks that extracting text from article body is equal after cleaning the html
    """
    raw_node = fromstring(item.raw_html, base_url=item.url)

    node = clean_node(raw_node, item.url)
    assert node != raw_node

    expected = cleaned_node_to_text(raw_node)
    actual = cleaned_node_to_text(node)
    assert actual == expected
