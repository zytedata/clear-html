from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from clear_html.clean import cleaned_node_to_text

from .utils import string_to_html_element

if TYPE_CHECKING:
    from lxml.html import HtmlElement


@pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ("<span>text inside</span>", "text inside"),
        ("<div>A<span>value</span></div>", "A value"),
        ("<div>Outside<figcaption>Inside</figcaption></div>", "Outside"),
    ],
)
def test_cleaned_node_to_text(test_input: str, expected: str) -> None:
    node = string_to_html_element(test_input)
    assert cleaned_node_to_text(node) == expected


def test_cleaned_node_to_text_with_custom_text_extractor() -> None:
    """Uses the optional text_extractor callable to see if it's used to extract
    the text in the node input."""

    def dummy_text_extractor(node: HtmlElement) -> str:
        """Returns the string 'dummy' irregardless of the node input contents"""
        return "dummy"

    node = string_to_html_element("<div>Any value</div>")
    assert cleaned_node_to_text(node, dummy_text_extractor) == "dummy"
