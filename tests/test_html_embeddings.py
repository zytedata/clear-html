from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from lxml.etree import tostring

from clear_html.html_embeddings import integrate_embeddings

from .utils import string_to_html_element

if TYPE_CHECKING:
    from lxml.html import HtmlElement


def normalize_nodes_to_string(nodes: set[HtmlElement]) -> set[str]:
    return {tostring(node).decode().strip() for node in nodes}


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ("<div>Got no whitelisted class</div>", set()),
        (
            "<div class='instagram-media'>Insta</div>",
            {'<div class="instagram-media">Insta</div>'},
        ),
        (
            """
            <div class="body">
                <div class='instagram-media'>Insta</div>
                <div class='fb-post'>Meta</div>
                <span>no whitelisted class</span>
            </div>
            """,
            {
                '<div class="instagram-media">Insta</div>',
                '<div class="fb-post">Meta</div>',
            },
        ),
    ],
)
def test_integrate_embeddings(test_input: str, expected: set[str]) -> None:
    node = string_to_html_element(test_input)
    result = integrate_embeddings(node)

    assert normalize_nodes_to_string(result) == expected


def test_integrate_embeddings_with_preprocessor() -> None:
    """Uses the optional preprocessor callable to see if it updates any of the
    whitelisted nodes.
    """

    def dummy_preprocessor(node: HtmlElement) -> None:
        """A simple preprocessor that replaces all 'a' chars within the node's
        textual data with 'X'."""
        if node.text:
            node.text = node.text.replace("a", "X")

    html = """
    <div class="body">
        <div class='instagram-media'>Insta</div>
        <div class='fb-post'>Meta</div>
        <span>no whitelisted class</span>
    </div>
    """
    node = string_to_html_element(html)
    result = integrate_embeddings(node, dummy_preprocessor)
    expected = {
        '<div class="instagram-media">InstX</div>',
        '<div class="fb-post">MetX</div>',
    }
    assert normalize_nodes_to_string(result) == expected
