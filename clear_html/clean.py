import copy
from typing import Callable, Optional

import html_text
from lxml.html import HtmlElement, tostring

from clear_html.formatted_text import clean_doc
from clear_html.html_embeddings import integrate_embeddings


def cleaned_node_to_text(
    node: HtmlElement, text_extractor: Optional[Callable] = None
) -> Optional[str]:
    """Format the given html tree as plain text, applying particular exclusions
    only applied to plain text (i.e. remove figure captions).
    Provided node should have been already cleaned to have expected output

    If provided, the optional ``text_extractor`` will be used to extract text
    from the given input node. Otherwise, ``html_text.extract_text`` is used.
    """
    node = copy.deepcopy(node)  # Need a copy if don't want to modify input node
    apply_text_exclusions(node)

    if text_extractor:
        return text_extractor(node)
    return html_text.extract_text(node, guess_layout=True)


def cleaned_node_to_html(node: HtmlElement) -> str:
    """
    Format the given html tree as html string.
    Provided node should have been already cleaned to have expected output

    >>> from lxml.html import fromstring
    >>> html = '<div></div>'
    >>> html = cleaned_node_to_html(fromstring(html))
    >>> print(html)
    <div></div>
    """
    return tostring(node, encoding="unicode", with_tail=False)


def clean_node(node: HtmlElement, url: Optional[str] = None) -> HtmlElement:
    """
    Normalize the given lxml node. The resultant node contains cleaned HTML,
    with embeddings preserved. Returns a copy so that the original
    node remains untouched.

    >>> from lxml.html import fromstring
    >>> html = '<div style="color=blue"><div>paragraph1</div><div>paragraph2</div></div>'
    >>> html = cleaned_node_to_html(clean_node(fromstring(html)))
    >>> print(html)
    <article>
    <BLANKLINE>
    <p>paragraph1</p>
    <BLANKLINE>
    <p>paragraph2</p>
    <BLANKLINE>
    </article>
    """
    node = copy.deepcopy(node)  # Need a copy if don't want to modify input node
    nodes_whitelist = integrate_embeddings(node)
    node = clean_doc(node, url, nodes_whitelist)
    return node


def apply_text_exclusions(node: HtmlElement):
    """Apply some additional exclusions that are needed to export the
    body as text. Modify given node."""
    exclude_figcaption(node)


def exclude_figcaption(node: HtmlElement):
    # Exclude html figcaption tag
    to_exclude = set(node.xpath(".//figcaption"))
    # Never exclude the node itself
    to_exclude -= {node}
    _drop_trees(to_exclude)


def _drop_trees(to_exclude):
    for el in to_exclude:
        if el.getparent() is not None:  # Parent cannot be removed
            el.drop_tree()
