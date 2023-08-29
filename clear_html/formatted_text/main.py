import copy
import unicodedata
from logging import warning
from typing import AbstractSet, List, Optional, Tuple
from urllib.parse import urljoin

from lxml.html import Element, HtmlElement, tostring  # noqa: F401
from lxml.html.clean import Cleaner

from clear_html.formatted_text.cleaner import BodyCleaner
from clear_html.formatted_text.defs import (
    ALLOWED_ATTRIBUTES,
    ALLOWED_TAGS,
    CAN_BE_EMPTY,
    MUST_ANCESTORS_FOR_DROP_CONTENT,
    MUST_ANCESTORS_FOR_KEEP_CONTENT,
    PHRASING_CONTENT,
)
from clear_html.formatted_text.figures import (
    clean_double_br_above_figcaption,
    clean_figcaptions_html,
    create_figures_from_isolated_figcaptions,
    infer_img_url_from_data_src_attr,
    remove_figures_without_content,
    top_level_media_within_figure,
)
from clear_html.formatted_text.headings import normalize_headings_level
from clear_html.formatted_text.utils import (
    clean_incomplete_structures,
    kill_tag_content,
    remove_empty_tags,
    set_article_tag_as_root,
    translate_tags,
)
from clear_html.lxml_utils import has_tail, has_text


def clean_doc(
    doc: HtmlElement,
    base_url: Optional[str],
    nodes_whitelist: AbstractSet[HtmlElement] = set(),
) -> HtmlElement:
    """Clean the tree. Mutate the doc. Root node could change,
    so final root is returned to avoid this effect. Nodes in ``node_whitelist``
    are preserved intact.

    See also a description of the overall approach in
    clear_html/formatted_text/__init__.py
    """
    if base_url is not None:
        make_links_absolute(doc, base_url)
    infer_img_url_from_data_src_attr(doc)
    translate_tags(doc, nodes_whitelist)
    remove_empty_tags(doc, white_list=CAN_BE_EMPTY)
    clean = _get_default_cleaner(nodes_whitelist)
    clean(doc)
    doc = set_article_tag_as_root(doc)
    normalize_headings_level(doc, nodes_whitelist)
    create_figures_from_isolated_figcaptions(doc)
    remove_figures_without_content(doc)
    clean_incomplete_structures(
        doc, MUST_ANCESTORS_FOR_KEEP_CONTENT, white_list=nodes_whitelist
    )
    clean_incomplete_structures(
        doc,
        MUST_ANCESTORS_FOR_DROP_CONTENT,
        preserve_content=False,
        white_list=nodes_whitelist,
    )
    clean_double_br_above_figcaption(doc)
    clean_figcaptions_html(doc)
    # Avoiding text extraction from iframes as usually they pollute
    # the text article
    kill_tag_content(doc, "iframe")
    paragraphy(doc)
    top_level_media_within_figure(doc, white_list=nodes_whitelist)
    almost_pretty_format(doc, base_url)
    return doc


def _get_default_cleaner(
    nodes_whitelist: Optional[AbstractSet[HtmlElement]] = None,
) -> Cleaner:
    cleaner = BodyCleaner(
        scripts=True,
        javascript=True,
        comments=True,
        style=True,
        inline_style=True,
        links=True,
        meta=True,
        processing_instructions=True,
        frames=True,
        remove_unknown_tags=False,
        safe_attrs_only=True,
        safe_attrs=ALLOWED_ATTRIBUTES,
        allow_tags=ALLOWED_TAGS,
        nodes_whitelist=nodes_whitelist,
    )
    # TODO: Use host_whitelist and whitelist_tags to control embeddings
    return cleaner


def paragraphy(doc: HtmlElement):
    """Ensures all textual content is inside a paragraph for first level.
    Removes sequences of consecutive br tags enclosing surroundings into
    paragraphs. Note that these kind of double
    br sequences could have been introduced by ``BodyCleaner`` function,
    of calls to ``drop_tag_preserve_spacing``
    and is in this function where we convert them to paragraphs
    when possible. Document is updated inline.
    """
    # Let's detect the sequences of consecutive br
    n_children = len(doc)
    br_sequences: List[Tuple[int, int]] = []
    start, end = None, None
    for idx, child in enumerate(doc):
        if child.tag == "br":
            if idx == 0 or doc[idx - 1].tag != "br" or has_tail(doc[idx - 1]):
                # A br without previous consecutive br was found
                start = idx
            if idx == n_children - 1 or doc[idx + 1].tag != "br" or has_tail(child):
                # A br without next consecutive br was found
                end = idx
                if start == end:
                    # Single br found. We don't do anything
                    start, end = None, None
                if start is not None and end is not None:
                    # Sequence of consecutive br found
                    br_sequences.append((start, end))
                    start, end = None, None

    # True for these children that are part of a br sequence
    force_split = [False] * n_children
    for start, end in br_sequences:
        force_split[start : end + 1] = [True] * (end - start + 1)

    # Let's split the node into different paragraphs
    br_sequences.append((n_children, n_children))  # To get last chunk included
    children = [copy.copy(c) for c in doc]
    del doc[:n_children]

    last_inline_chunk: List[HtmlElement] = []
    include_root_text = True

    def push_accumulated_content_as_p(idx):
        # Pushes content in last_inline_chunk in
        # a new paragraph.
        nonlocal include_root_text, doc, children, last_inline_chunk
        p = Element("p")
        p.extend(last_inline_chunk)
        if include_root_text:
            p.text = doc.text and doc.text.lstrip()
            doc.text = None
            include_root_text = False
        else:
            before_last_chunk_idx = idx - len(last_inline_chunk) - 1
            tail = children[before_last_chunk_idx].tail
            p.text = tail and tail.rstrip()
            children[before_last_chunk_idx].tail = None
        last_inline_chunk.clear()
        if has_text(p) or len(p) > 0:
            # Only add non-empty paragraphs
            doc.append(p)

    for idx, el in enumerate(children):
        if el.tag in PHRASING_CONTENT and not force_split[idx]:
            # Selecting chunks of textual content (inline tags are part of it)
            last_inline_chunk.append(el)
        else:
            # No inline tag or forced split, let's split.
            # Push last textual content chunk
            push_accumulated_content_as_p(idx)
            # Push current node but not if the split was forced
            if not force_split[idx]:
                doc.append(el)

    push_accumulated_content_as_p(n_children)


def almost_pretty_format(doc: HtmlElement, url: Optional[str] = None):
    """Format doc to have a good looking when serialized as html.
    Only modifying first level of the body which is safe (formatting
    inner elements is not that safe). One line of separation for first
    level elements and some leading and trailing striping for better looking

     >>> from lxml.html import fromstring
     >>> html = "<div>   <p>  1</p>   <p>  2   </p> <p>  <em>3</em>rd   </p> <pre> pre </pre></div>"
     >>> html = fromstring(html)
     >>> almost_pretty_format(html)
     >>> print(tostring(html).decode())
     <div>
     <BLANKLINE>
     <p>1</p>
     <BLANKLINE>
     <p>2</p>
     <BLANKLINE>
     <p><em>3</em>rd</p>
     <BLANKLINE>
     <pre> pre </pre>
     <BLANKLINE>
     </div>
    """
    url = url or ""
    if has_text(doc):
        warning(
            f"Unexpected text found '{doc.text}' for url '{url}' in root"
            f" node or article body. Removing it and going ahead."
        )
    doc.text = "\n\n"
    for child in doc:
        if has_tail(child):
            warning(
                f"Unexpected text found '{doc.tail}' for url '{url}' in "
                f"the tail of a first level child of the article body node. "
                f"Removing it and going ahead."
            )
        child.tail = "\n\n"
        if child.tag != "pre":
            child.text = (child.text or "").lstrip()
            if len(child) > 0:
                child[-1].tail = (child[-1].tail or "").rstrip()
            else:
                child.text = child.text.rstrip()


def make_links_absolute(doc: HtmlElement, base_url: str):
    """Like doc.make_links_absolute which ignores errors,
    but also does not fail on urls with escape chars, skipping them instead.
    """
    # based on doc.rewrite_links
    for el, attrib, link, pos in doc.iterlinks():
        try:
            new_link = urljoin(base_url, link.strip())
        except ValueError:
            continue
        if new_link == link:
            continue

        if attrib is None:
            # attrib is only None when el is <style> with links in the text
            assert el.text is not None
            new = el.text[:pos] + new_link + el.text[pos + len(link) :]
            try:
                el.text = new
            except ValueError:
                pass
        else:
            cur = el.get(attrib)
            assert cur is not None
            if not pos and len(cur) == len(link):
                new = new_link  # most common case
            else:
                new = cur[:pos] + new_link + cur[pos + len(link) :]
            try:
                el.set(attrib, new)
            except ValueError:
                new = "".join(c for c in new if unicodedata.category(c) != "Cc")
                try:
                    el.set(attrib, new)
                except ValueError:
                    pass
