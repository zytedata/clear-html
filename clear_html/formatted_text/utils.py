from typing import AbstractSet, Callable, Mapping, Optional

from lxml.html import Element, HtmlElement, fromstring, tostring

from clear_html.formatted_text.defs import MUST_ANCESTORS_FOR_DROP_CONTENT  # noqa: F401
from clear_html.formatted_text.defs import MUST_ANCESTORS_FOR_KEEP_CONTENT  # noqa: F401
from clear_html.formatted_text.defs import (
    ALLOWED_TAGS,
    CONTENT_EVEN_IF_EMPTY,
    HTML_UNIVERSE_TAGS,
    PHRASING_CONTENT,
    TAG_TRANSLATIONS,
)
from clear_html.lxml_utils import (
    ChildrenSlice,
    has_tail,
    has_text,
    prev_text,
    wrap_element_with_tag,
)


def translate_tags(doc: HtmlElement, white_list: AbstractSet[HtmlElement] = set()):
    """Translate tag names (i.e. b -> strong). Mutates the doc.
    Nodes in the white list are ignored.

     >>> html = fromstring("<p><b><i>text</i></b></p>")
     >>> translate_tags(html)
     >>> tostring(html).decode()
     '<p><strong><em>text</em></strong></p>'
    """
    for n in doc.iter():
        if n in white_list:
            continue
        translation = TAG_TRANSLATIONS.get(n.tag, None)
        if translation is not None:
            n.tag = translation


def set_article_tag_as_root(doc: HtmlElement) -> HtmlElement:
    """Ensures that root tag is ``article``. It can
    return a new element. Mutates the doc.

     >>> html = fromstring("<p>text</p>")
     >>> tostring(set_article_tag_as_root(html)).decode()
     '<article><p>text</p></article>'

     >>> html = fromstring("<section><p>text</p></section>")
     >>> tostring(set_article_tag_as_root(html)).decode()
     '<article><p>text</p></article>'
    """
    if doc.tag in ALLOWED_TAGS:
        # Creating a new root node enclosing doc
        doc = wrap_element_with_tag(doc, "article")
    else:
        # Else, we just reuse this tag. Remember that root node is never
        # clean up by the cleaner.
        doc.tag = "article"
        doc.attrib.clear()
    return doc


def wrap_tags(
    doc: HtmlElement,
    to_be_enclosed_tags: AbstractSet,
    enclosing_tag: str,
    node_check: Callable[[HtmlElement], bool] = lambda x: True,
    transparent_tags: AbstractSet = set(),
):
    """Enclose the elements with tag `to_be_enclosed_tags` within a tag
    `enclosing_tag` if they are not already enclosed, that is, if `enclosing_tag`
    is not already an ancestor. All transparent tags without more content
    than the element to enclose itself will be also included in the enclosed
    element (useful for enclosing ``<a><img>`` into ``<figure>``.
    """
    ancestors_tags = {doc.tag}
    for child in doc:
        _wrap_tags_with(
            child,
            to_be_enclosed_tags,
            enclosing_tag,
            ancestors_tags,
            node_check=node_check,
            transparent_tags=transparent_tags,
        )


def _wrap_tags_with(
    doc: HtmlElement,
    to_be_enclosed_tags: AbstractSet,
    enclosing_tag: str,
    ancestors_tags: AbstractSet = set(),
    node_check: Callable[[HtmlElement], bool] = lambda x: True,
    transparent_tags: AbstractSet = set(),
):
    ancestors_tags = ancestors_tags | {doc.tag}
    if (
        (enclosing_tag not in ancestors_tags)
        and doc.tag in to_be_enclosed_tags
        and node_check(doc)
    ):
        # We have to enclose. Skipping all the parent tags that are
        # transparent and doesn't have other content
        to_enclose_el = doc
        parent = doc.getparent()
        while parent is not None and parent.tag in transparent_tags:
            if len(parent) != 1 or has_text(parent):
                break
            to_enclose_el = parent
            parent = parent.getparent()
        wrap_element_with_tag(to_enclose_el, enclosing_tag)
        return
    for child in doc:
        _wrap_tags_with(
            child,
            to_be_enclosed_tags,
            enclosing_tag,
            ancestors_tags,
            node_check,
            transparent_tags,
        )


def remove_empty_tags(
    doc: HtmlElement, white_list: AbstractSet[str] = set(), _root=True
):
    """Removes empty tags, but skipping the `white_list` ones

    >>> html = fromstring("<article><p><em></em></p></article>")
    >>> remove_empty_tags(html)
    >>> tostring(html).decode()
    '<article></article>'

    >>> html = fromstring("<article><p><em></em></p></article>")
    >>> remove_empty_tags(html, {'p'})
    >>> tostring(html).decode()
    '<article><p></p></article>'
    """
    for el in doc:
        remove_empty_tags(el, white_list, False)
    if doc.tag not in white_list and len(doc) == 0 and not has_text(doc) and not _root:
        doc.drop_tag()


def drop_tag_preserve_spacing(doc: HtmlElement, preserve_content=True):
    """Drops a tag keeping its content. If element to be removed
    is a block element, leading or trailing double br tags would
    be introduced to preserve spacing. If preserve_content is
    false, the entire tree will be deleted (but preserving spacing).
    """
    parent = doc.getparent()
    if parent is None:
        return  # Root node cannot be removed

    if not is_phrasing_content(doc):
        # If tag to remove is a block tag then we should
        # carefully add double brs in some cases to
        # respect the separation between text chunks
        # Not known html tags are considered as inline elements by default.
        idx = parent.index(doc)

        prev_is_inline = (
            idx != 0
            and parent[idx - 1].tag in PHRASING_CONTENT
            and not _double_br(parent, idx - 2, idx - 1)
        )
        after_is_inline = (
            idx != len(parent) - 1
            and parent[idx + 1].tag in PHRASING_CONTENT
            and not _double_br(parent, idx + 1, idx + 2)
        )

        has_text_prev = bool(prev_text(doc).strip()) or prev_is_inline
        has_text_inside = preserve_content and (has_text(doc) or len(doc) > 0)
        has_text_after = has_tail(doc) or after_is_inline

        if has_text_prev and (has_text_inside or has_text_after):
            # Insert double br before
            for i in range(2):
                parent.insert(idx, Element("br"))
            idx += 2
        if has_text_inside and has_text_after:
            # Insert brs after
            last_br = Element("br")
            last_br.tail = doc.tail
            doc.tail = None
            parent.insert(idx + 1, last_br)
            parent.insert(idx + 1, Element("br"))
    if preserve_content:
        doc.drop_tag()
    else:
        doc.drop_tree()


def _double_br(doc: HtmlElement, start: int, end: int):
    """True if double br in doc[start:end] (end-start must be 1)"""
    if end - start != 1:
        return False
    if not all(idx >= 0 and idx < len(doc) for idx in (start, end)):
        return False
    both_brs = (doc[start].tag == "br") and (doc[end].tag == "br")
    return both_brs and not has_tail(doc[start])


def has_no_content(doc: HtmlElement) -> bool:
    """Checks if a node contains content. A node has content if it has
    any text in the tree or if has any tags that handle non textual
    content like ``img`` or ``iframe``. ``br``, ``dt``, ``dd``, ``td`` tags are
    considered as non content. Implementation detail: a copy of the doc is done.

    >>> has_no_content(fromstring("<div>hello</div>"))
    False
    >>> has_no_content(fromstring("<div></div>"))
    True
    >>> has_no_content(fromstring("<img></img>"))
    False
    >>> has_no_content(fromstring("<div><img></img></div>"))
    False
    >>> has_no_content(fromstring("<div><div></div></div>"))
    True
    >>> has_no_content(fromstring("<div><div></div></div>"))
    True
    >>> has_no_content(fromstring("<div><div></div>hey</div>"))
    False
    >>> has_no_content(fromstring("<div><div>hey</div></div>"))
    False
    >>> has_no_content(fromstring("<div>hey<div></div></div>"))
    False
    """
    return is_empty(doc, tags_with_content_even_if_empty=CONTENT_EVEN_IF_EMPTY)


def is_empty(
    doc: HtmlElement, tags_with_content_even_if_empty: AbstractSet[str] = set()
):
    """Checks if given doc is an empty tag or tag formed with empty tags.
    ``tags_with_content_even_if_empty`` tags are considered as having content
    even if empty.

    >>> is_empty(fromstring("<div>hello</div>"))
    False
    >>> is_empty(fromstring("<div></div>"))
    True
    >>> is_empty(fromstring("<div><div/></div>"))
    True
    >>> is_empty(fromstring("<div><div/><div/></div>"))
    True
    >>> is_empty(fromstring("<div>a<div/><div/></div>"))
    False
    >>> is_empty(fromstring("<div><div/>a<div/></div>"))
    False
    >>> is_empty(fromstring("<div><div/><div/>a</div>"))
    False
    >>> is_empty(fromstring("<div><div>a</div><div/>a</div>"))
    False
    """
    empty = True
    for el in doc:
        empty = is_empty(el, tags_with_content_even_if_empty) and not has_tail(el)
        if not empty:
            break
    return (
        doc.tag not in tags_with_content_even_if_empty and empty and not has_text(doc)
    )


def is_phrasing_content(doc: HtmlElement):
    """'Phrasing content is the text of the document, as well as elements that
    mark up that text at the intra-paragraph level'
    (see https://html.spec.whatwg.org/#phrasing-content). This method return
    true if the element tag is one of those mark up allowed in paragraphs.
    Unknown tags are considered as phrasing elements by default."""
    return doc.tag in PHRASING_CONTENT or doc.tag not in HTML_UNIVERSE_TAGS


def group_with_previous_content_block(doc: HtmlElement) -> Optional[ChildrenSlice]:
    """Return a ChildrenSlice that groups current node content block with
    previous content block. Return None if doc is the root.

    >>> tostr = lambda x: f"{x.node.tag}, {x.start}, {x.end}" if x else 'None'
    >>> html = fromstring("<article><p>hey</p><p></p><figcaption>fig</figcaption><p></p></article>")
    >>> tostr(group_with_previous_content_block(html.find(".//figcaption")))
    'article, 0, 3'

    >>> tostr = lambda x: f"{x.node.tag}, {x.start}, {x.end}" if x else 'None'
    >>> html = fromstring("<article><p>hey</p><p><div><div>end</div><figcaption>fig</figcaption></div></article>")
    >>> tostr(group_with_previous_content_block(html.find(".//figcaption")))
    'div, 0, 2'

    >>> tostr = lambda x: f"{x.node.tag}, {x.start}, {x.end}" if x else 'None'
    >>> html = fromstring("<article><p>hey</p><p><div><figcaption>fig</figcaption><div>end</div></div></article>")
    >>> tostr(group_with_previous_content_block(html.find(".//figcaption")))
    'None'

    >>> html = fromstring(
    ...   "<article><p>hey</p>text<p><figcaption>fig</figcaption></p></article>")
    >>> tostr(group_with_previous_content_block(html.find(".//figcaption")))
    'None'

    >>> html = fromstring(
    ...   "<article><p>hey</p>text<p><figcaption>fig</figcaption></p></article>")
    >>> tostr(group_with_previous_content_block(html.find(".//figcaption")))
    'None'

    >>> html = fromstring(
    ...   "<article><p>hey</p><div><br></div><p></p><figcaption>fig</figcaption><p></p></article>")
    >>> tostr(group_with_previous_content_block(html.find(".//figcaption")))
    'article, 0, 4'
    """
    parent = doc.getparent()
    if parent is None:
        return None
    idx = parent.index(doc)
    first_with_content_idx = find_previous_non_empty_sibling(doc)
    if first_with_content_idx is not None:
        return ChildrenSlice(parent, first_with_content_idx, idx + 1)
    elif len(parent) == 1 and not has_text(parent) and not has_tail(doc):
        return group_with_previous_content_block(parent)
    else:
        return None


def find_previous_non_empty_sibling(doc: HtmlElement) -> Optional[int]:
    """
    >>> html = fromstring("<div><div>end</div>t<figcaption>fig</figcaption></div>")
    >>> find_previous_non_empty_sibling(html.find(".//figcaption"))

    >>> html = fromstring("<div><div>end</div><figcaption>fig</figcaption></div>")
    >>> find_previous_non_empty_sibling(html.find(".//figcaption"))
    0

    >>> html = fromstring("<div><div></div><figcaption>fig</figcaption></div>")
    >>> find_previous_non_empty_sibling(html.find(".//figcaption"))
    """
    parent = doc.getparent()
    if parent is None:
        return None
    candidate_idx = parent.index(doc) - 1
    while candidate_idx >= 0 and (
        has_tail(parent[candidate_idx]) or has_no_content(parent[candidate_idx])
    ):
        candidate_idx -= 1
    if candidate_idx >= 0:
        return candidate_idx
    else:
        return None


def _test_fn(fn):
    def func(doc):
        html = fromstring(doc)
        fn(html)
        return tostring(html).decode()

    return func


def clean_incomplete_structures(
    doc: HtmlElement,
    rules: Mapping[str, AbstractSet[str]],
    preserve_content=True,
    white_list: AbstractSet[HtmlElement] = set(),
):
    """Drop tags (keeping content) of incomplete structures.
    For example, removes a td element if not belonging to any table.
    Never clean the base element. If preserve_content is false then nodes
    are completely removed without keeping content (but preserving spacing).
    Nodes in the white list are ignored.

     >>> def clean(html, rules=MUST_ANCESTORS_FOR_KEEP_CONTENT,
     ...           preserve_content=True):
     ...    html = fromstring(html)
     ...    clean_incomplete_structures(html, rules, preserve_content)
     ...    print(tostring(html).decode())

     >>> clean("<div>pre<table><tbody><tr><td>text</td></tr></tbody></table>post</div>")
     <div>pre<table><tbody><tr><td>text</td></tr></tbody></table>post</div>

     >>> clean("<div><dt>key</dt><dd>value</dd></td>")
     <div>key<br><br>value</div>

     >>> clean("<div>A<dt>key</dt>text<dd>value</dd>to preserve</td>", preserve_content=False)
     <div>A<br><br>text<br><br>to preserve</div>

     >>> clean("<div>pre<dt>key</dt><dd>value</dd>post</td>")
     <div>pre<br><br>key<br><br>value<br><br>post</div>

     >>> clean("<div>pre<figcaption>f</figcaption>post</td>", MUST_ANCESTORS_FOR_DROP_CONTENT, False)
     <div>pre<br><br>post</div>
    """
    for child in doc:
        _clean_incomplete_structures(
            child, rules, {doc.tag}, preserve_content, white_list
        )


def _clean_incomplete_structures(
    doc: HtmlElement,
    rules: Mapping[str, AbstractSet[str]],
    ancestors_tags: AbstractSet = set(),
    preserve_content=True,
    white_list: AbstractSet[HtmlElement] = set(),
):
    ancestors_tags = ancestors_tags | {doc.tag}
    for child in doc:
        _clean_incomplete_structures(child, rules, ancestors_tags, preserve_content)
    required_ancestors = rules.get(doc.tag, None)
    if (
        required_ancestors is not None
        and not (ancestors_tags & required_ancestors)
        and doc not in white_list
    ):
        drop_tag_preserve_spacing(doc, preserve_content)


def kill_tag_content(doc: HtmlElement, tag: str):
    """Removes the content of all these tags found in the doc

    >>> def kill(html):
    ...    html = fromstring(html)
    ...    kill_tag_content(html, 'iframe')
    ...    print(tostring(html).decode())

    >>> kill('<div><iframe cls="pepe">h<p>e</p>l<p>o</p></iframe></div>')
    <div><iframe cls="pepe"></iframe></div>

    >>> kill('<div><iframe cls="pepe">h<p>e</p>l<p>o</p><iframe cls="pepe">h<p>e</p>l<p>o</p></iframe></iframe></div>')
    <div><iframe cls="pepe"></iframe></div>

    >>> kill('<div>a<br/>a<iframe cls="pepe">h<p>e</p></iframe>a<br/>a</div>')
    <div>a<br>a<iframe cls="pepe"></iframe>a<br>a</div>
    """
    for el in doc.xpath(f".//{tag}"):
        el.text = None
        del el[: len(el)]
