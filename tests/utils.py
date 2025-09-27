from __future__ import annotations

from typing import TYPE_CHECKING, cast

import parsel

if TYPE_CHECKING:
    from lxml.html import HtmlElement


def string_to_html_element(html: str) -> HtmlElement:
    return cast("HtmlElement", parsel.Selector(html).root)
