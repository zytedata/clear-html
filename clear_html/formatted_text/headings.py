from typing import AbstractSet, List

from lxml.html import HtmlElement, fromstring, tostring  # noqa: F401

from clear_html.lxml_utils import wrap_element_content_with_tag


def headings_nodes(doc: HtmlElement) -> List[HtmlElement]:
    return doc.xpath(
        ".//*[self::h1 or self::h2 or self::h3 or" " self::h4 or self::h5 or self::h6]"
    )


def min_heading(doc: HtmlElement) -> int:
    """Return the min heading level in the document"""
    return min([int(h.tag[1:]) for h in headings_nodes(doc)], default=1)


def normalize_headings_level(
    doc: HtmlElement, white_list: AbstractSet[HtmlElement] = set()
):
    """Normalizes headings in the doc so that the lowest level is always 2.
    If six levels document is found, the last level is replaced by
    ``<p><strong></strong></p>``
    Nodes in the white list are ignored.

    >>> html = fromstring("<a><h1></h1><h2></h2><h3></h3></a>")
    >>> normalize_headings_level(html)
    >>> tostring(html).decode()
    '<a><h2></h2><h3></h3><h4></h4></a>'

    >>> html = fromstring("<a><h1></h1><h6>Hola<em>que tal</em>colega</h6></a>")
    >>> normalize_headings_level(html)
    >>> tostring(html).decode()
    '<a><h2></h2><p><strong>Hola<em>que tal</em>colega</strong></p></a>'

    """
    root_level = min_heading(doc)
    for h in headings_nodes(doc):
        if h in white_list:
            continue
        if h.tag != "h6":
            # Headings starting in h2
            h.tag = "h" + str(int(h.tag[1:]) - root_level + 2)
        else:
            # Six heading replaced by <p><strong></strong></p>
            h.tag = "p"
            wrap_element_content_with_tag(h, "strong")
