import copy  # noqa: F401
from typing import Any, Generator, List, Optional

import attr
from lxml.html import Element, HtmlElement, fromstring, tostring  # noqa: F401


def wrap_element_content_with_tag(doc: HtmlElement, tag: str) -> HtmlElement:
    """Enclose the whole content of the given doc within a new and single
    child. The new created element is returned. Doc is
    updated in place.

    >>> html = fromstring("<a>h<b>e</b>l</a>")
    >>> el = wrap_element_content_with_tag(html, 'tag')
    >>> tostring(html).decode()
    '<a><tag>h<b>e</b>l</tag></a>'

    >>> html = fromstring("<a>h<b>e</b>l<c>h1</c>t1</a>")
    >>> el = wrap_element_content_with_tag(html.find('c'), 'tag')
    >>> tostring(html).decode()
    '<a>h<b>e</b>l<c><tag>h1</tag></c>t1</a>'
    """
    wrapper = Element(tag)
    for child in doc:
        wrapper.insert(len(wrapper), child)

    doc.insert(0, wrapper)
    wrapper.text = doc.text
    doc.text = None
    return wrapper


def wrap_element_with_tag(doc: HtmlElement, tag: str) -> HtmlElement:
    """Enclose the given doc within a new tag maintaining
    the tree structure. The new created element is returned.
    Doc is updated in place.

    >>> html = fromstring("<a>h<b>e</b>l<c>l</c>o</a>")
    >>> tostring(wrap_element_with_tag(html, 'tag')).decode()
    '<tag><a>h<b>e</b>l<c>l</c>o</a></tag>'

    >>> html = fromstring("<a>h<b>e</b>l<c>l</c>o</a>")
    >>> el = wrap_element_with_tag(html.find('b'), 'tag')
    >>> tostring(html).decode()
    '<a>h<tag><b>e</b></tag>l<c>l</c>o</a>'
    """
    parent = doc.getparent()
    wrapper = Element(tag)
    wrapper.tail = doc.tail
    doc.tail = None
    if parent is not None:
        idx = parent.index(doc)
        parent.remove(doc)
        parent.insert(idx, wrapper)
    wrapper.insert(0, doc)
    return wrapper


def str_has_content(text: Optional[str]):
    return bool(text and text.strip())


def has_text(doc: HtmlElement):
    return str_has_content(doc.text)


def has_tail(doc: HtmlElement):
    return str_has_content(doc.tail)


def prev_text(doc: HtmlElement) -> str:
    """Return the text previous to the given node.
    Previous is parent text for first child nodes.

    >>> html = fromstring("<a>h<b>e</b>l<c>z</c>o</a>")
    >>> prev_text(html)
    ''
    >>> prev_text(html.find(".//b"))
    'h'
    >>> prev_text(html.find(".//c"))
    'l'
    """
    parent = doc.getparent()
    if parent is None:
        return ""
    idx = parent.index(doc)
    if idx == 0:
        text = parent.text
    else:
        text = parent[idx - 1].tail
    return text or ""


def iter_deep_first_post_order(doc: HtmlElement) -> Generator[HtmlElement, Any, None]:
    """Iterate over a document in a deep first fashion returning
    elements post-order https://en.wikipedia.org/wiki/Tree_traversal#Post-order_(LRN)"""
    for el in doc:
        yield from iter_deep_first_post_order(el)
    yield doc


@attr.s(auto_attribs=True)
class ChildrenSlice:
    """Represents a slice of children withing a node. ``node[start:end]``.
    The slice containing root node is represented by a ``None`` node"""

    node: HtmlElement
    start: int
    end: int


def wrap_children_slice(slice: ChildrenSlice, tag: str) -> HtmlElement:
    """Wraps a slice of children into the same tag.
    Return new created tag.

    >>> orig_html = fromstring("<b>w<b1></b1>x<b2></b2>y<b3></b3>z</b>")
    >>> html = copy.deepcopy(orig_html)
    >>> _ = wrap_children_slice(ChildrenSlice(html, 0, 3), 'div')
    >>> tostring(html).decode()
    '<b>w<div><b1></b1>x<b2></b2>y<b3></b3></div>z</b>'
    >>> html = copy.deepcopy(orig_html)
    >>> _ = wrap_children_slice(ChildrenSlice(html, 0, 1), 'div')
    >>> tostring(html).decode()
    '<b>w<div><b1></b1></div>x<b2></b2>y<b3></b3>z</b>'
    >>> html = copy.deepcopy(orig_html)
    >>> _ = wrap_children_slice(ChildrenSlice(html, 2, 3), 'div')
    >>> tostring(html).decode()
    '<b>w<b1></b1>x<b2></b2>y<div><b3></b3></div>z</b>'
    """
    parent, start, end = slice.node, slice.start, slice.end
    content = parent[start:end]
    new_tag = Element(tag)
    new_tag.tail = parent[end - 1].tail
    parent[end - 1].tail = None
    del parent[start:end]
    new_tag.extend(content)
    parent.insert(start, new_tag)
    return new_tag


def ancestors(
    node: HtmlElement, max: Optional[int] = None, stop_at: Optional[HtmlElement] = None
) -> List[HtmlElement]:
    """Return the ancestors of a node ordered by distance.

    >>> tags = lambda x: list(map(lambda n: n.tag, x))
    >>> nodes = [Element(tag) for tag in 'abcde']
    >>> for i in range(1,len(nodes)):
    ...     nodes[i-1].insert(0, nodes[i])

    >>> tags(ancestors(nodes[4]))
    ['d', 'c', 'b', 'a']
    >>> tags(ancestors(nodes[4], 0))
    []
    >>> tags(ancestors(nodes[4], 2))
    ['d', 'c']
    >>> tags(ancestors(nodes[4], 200))
    ['d', 'c', 'b', 'a']
    >>> tags(ancestors(nodes[0], 200))
    []
    >>> tags(ancestors(nodes[4], stop_at=nodes[1]))
    ['d', 'c', 'b']

    """
    ret: List[HtmlElement] = []
    while (parent := node.getparent()) is not None and (max is None or len(ret) < max):
        ret.append(parent)
        node = parent
        if stop_at is not None and node == stop_at:
            break
    return ret


def _traverse_until_level(doc: HtmlElement, level: int, max_level: Optional[int]):
    if max_level is None or level <= max_level:
        yield doc
    for child in doc:
        yield from _traverse_until_level(child, level + 1, max_level)


def descendants(node: HtmlElement, max_level=None) -> List[HtmlElement]:
    """Return the descendant nodes of a given nodes until a particular level.
    All descendants are returned If no ``max_level`` is provided.

    >>> tags = lambda x: list(map(lambda n: n.tag, x))
    >>> html = fromstring("<html><body><b><b1><b11></b11></b1><b2></b2><b3></b3></b></body></html>")
    >>> tags(descendants(html.find(".//b11")))
    []
    >>> tags(descendants(html.find(".//b")))
    ['b1', 'b11', 'b2', 'b3']
    >>> tags(descendants(html.find(".//b"))) == tags(descendants(html.find(".//b"), 2))
    True
    >>> tags(descendants(html.find(".//b"), 0))
    []
    >>> tags(descendants(html.find(".//b"), 1))
    ['b1', 'b2', 'b3']
    """
    return list(_traverse_until_level(node, 0, max_level))[1:]
