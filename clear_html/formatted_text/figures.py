from typing import AbstractSet, cast

from lxml.html import HtmlElement, fromstring, tostring  # noqa: F401
from lxml.html.clean import Cleaner

from clear_html.formatted_text.cleaner import BodyCleaner
from clear_html.formatted_text.defs import MUST_ANCESTORS_FOR_KEEP_CONTENT  # noqa: F401
from clear_html.formatted_text.defs import (
    ALLOWED_ATTRIBUTES,
    FIGURE_CAPTION_ALLOWED_TAGS,
    FIGURE_CONTENT_TAGS,
    MUST_ANCESTORS_FOR_KEEP_CONTENT_REVERSED,
    TRANSPARENT_CONTENT,
    WRAPPED_WITH_FIGURE,
)
from clear_html.formatted_text.utils import _test_fn  # noqa: F401
from clear_html.formatted_text.utils import clean_incomplete_structures  # noqa: F401
from clear_html.formatted_text.utils import (
    drop_tag_preserve_spacing,
    group_with_previous_content_block,
    wrap_tags,
)
from clear_html.lxml_utils import (
    ChildrenSlice,
    ancestors,
    descendants,
    has_tail,
    has_text,
    wrap_children_slice,
)


def _get_figure_caption_cleaner() -> Cleaner:
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
        allow_tags=FIGURE_CAPTION_ALLOWED_TAGS,
    )
    return cleaner


def enclose_media_within_figure(doc: HtmlElement):
    """Ensures all media (images, videos, etc) are enclosed within figures.
    If possible, images with
    a link also includes the link within the figure element."""
    wrap_tags(
        doc,
        to_be_enclosed_tags=WRAPPED_WITH_FIGURE,
        enclosing_tag="figure",
        transparent_tags=TRANSPARENT_CONTENT,
    )


def top_level_media_within_figure(
    doc: HtmlElement, white_list: AbstractSet[HtmlElement] = set()
):
    """Enclose top level isolated multimedia into figures. In other words,
    paragraphs containing only a single media element are replaced by a figure.
    Nodes in the white list are ignored.

    >>> apply = _test_fn(top_level_media_within_figure)

    >>> apply("<div><p><a><img></a></p></div>")
    '<div><figure><a><img></a></figure></div>'
    >>> apply("<div><p><a>t<img></a></p></div>")
    '<div><p><a>t<img></a></p></div>'
    >>> apply("<div><p>a<img></p></div>")
    '<div><p>a<img></p></div>'
    >>> apply("<div><p>a<img></p></div>")
    '<div><p>a<img></p></div>'
    >>> apply("<div><p><img>a</p></div>")
    '<div><p><img>a</p></div>'
    >>> apply("<div><p><audio><source></source></audio></p></div>")
    '<div><figure><audio><source></source></audio></figure></div>'
    """

    def is_single_tag(el: HtmlElement):
        return len(el) == 1 and not has_text(el) and not has_tail(el[0])

    for child in doc:
        if (child.tag == "p") and is_single_tag(child) and child not in white_list:
            single_p = child
            p_child = single_p[0]
            if p_child.tag in FIGURE_CONTENT_TAGS:
                single_p.tag = "figure"
            elif p_child.tag == "a" and is_single_tag(p_child):
                if p_child[0].tag in FIGURE_CONTENT_TAGS:
                    single_p.tag = "figure"


def infer_img_url_from_data_src_attr(doc: HtmlElement):
    """Fills src attribute from data-src for img tags.
    It is common to see img tags without src attribute but with data-src

     >>> html = fromstring("<article><img data-src='img.jpg'></article>")
     >>> infer_img_url_from_data_src_attr(html)
     >>> tostring(html).decode()
     '<article><img data-src="img.jpg" src="img.jpg"></article>'
    """
    for el in doc.iterfind(".//img"):
        if not el.get("src") and el.get("data-src"):
            el.attrib["src"] = cast(str, el.get("data-src"))


def create_figures_from_isolated_figcaptions(node: HtmlElement):
    """Wraps isolated figcaptions with the content above and form a new figure.
    Mutates node.

    >>> html = fromstring(
    ...     "<article>"
    ...         "<figure>"
    ...             "<img href='link1'/>"
    ...             "<figcaption>caption1</figcaption>"
    ...         "</figure>"
    ...         "<img href='link2'/>"
    ...         "<figcaption>caption2</figcaption>"
    ...         "<p>text3</p>"
    ...         "<br>"
    ...         "<figcaption>caption3</figcaption>"
    ...         "<figure>"
    ...             "<img href='link4'/>"
    ...             "<figcaption>caption4</figcaption>"
    ...         "</figure>"
    ...         "<figcaption>caption4_2</figcaption>"
    ...     "</article>")
    >>> create_figures_from_isolated_figcaptions(html)
    >>> tostring(html).decode()
    '<article><figure><img href="link1"><figcaption>caption1</figcaption></figure><figure><img href="link2"><figcaption>caption2</figcaption></figure><p>text3</p><br><figcaption>caption3</figcaption><figure><img href="link4"><figcaption>caption4<br><br>caption4_2</figcaption></figure></article>'

    >>> html = fromstring(
    ...     "<article>"
    ...         "<table>"
    ...             "<tr><td><img href='link1'/></td></tr>"
    ...             "<tr><td><figcaption>caption1</figcaption></td></tr>"
    ...         "</table>"
    ...     "</article>")
    >>> create_figures_from_isolated_figcaptions(html)
    >>> clean_incomplete_structures(html, MUST_ANCESTORS_FOR_KEEP_CONTENT)
    >>> tostring(html).decode()
    '<article><figure><img href="link1"><br><br><figcaption>caption1</figcaption></figure></article>'
    """
    for caption in node.xpath(".//figcaption"):
        slice = group_with_previous_content_block(caption)
        if slice:
            anctrs = ancestors(caption, stop_at=node)
            ancestors_tags = [n.tag for n in anctrs]
            # Avoiding creating the figure if previous selected content is
            # a paragraph. Ideally a figure could be formed by text, but
            # I have seen that Splash sometimes with JS disabled is rendering
            # images in such a way that they are non visible,
            # and they are then removed so
            # finally a figure was formed with a the paragraph before, which
            # is wrong. It is safe then not to form the figure and so the caption
            # will be just removed.
            prev_content_node = slice.node[slice.start]
            prev_content_is_paragraph = (
                prev_content_node.tag == "p"
                and not FIGURE_CONTENT_TAGS
                & {n.tag for n in descendants(prev_content_node)}
            )
            if "figure" not in ancestors_tags and not prev_content_is_paragraph:
                if slice.node.tag in [
                    "table",
                    "tbody",
                    "thead",
                    "tfoot",
                    "dl",
                    "ul",
                    "ol",
                ]:
                    # The new figure could be breaking some table, definition list
                    # or list. If this is the case, we opt by dissolving such
                    # structure. For doing that it is enough to replace the root element
                    # tag of the structure for a children of the structure
                    # (i.e. change ``table`` by ``tr``). Another method will
                    # take care later of removing the rest of the incomplete
                    # structure.
                    for ancestor in anctrs:
                        if (
                            ancestor.tag
                            in MUST_ANCESTORS_FOR_KEEP_CONTENT_REVERSED.keys()
                        ):
                            ancestor.tag = MUST_ANCESTORS_FOR_KEEP_CONTENT_REVERSED[
                                ancestor.tag
                            ]
                            break
                new_figure = wrap_children_slice(slice, "figure")
                # Case when figure was at the same level that caption.
                # This avoids having figures inside figures in this case.
                for inner_figure in new_figure.xpath(".//figure"):
                    drop_tag_preserve_spacing(inner_figure)
                fuse_figcaptions(new_figure)


def fuse_figcaptions(figure: HtmlElement):
    """Fuses first block of consecutive figcaptions and remove the rest found.

    >>> fuse = _test_fn(fuse_figcaptions)

    >>> fuse("<figure><img/><figcaption>c1</figcaption><figcaption>c2</figcaption>end</figure>")
    '<figure><img><figcaption>c1<br><br>c2</figcaption>end</figure>'

    >>> fuse("<figure><img/><figcaption>c1</figcaption>middle<figcaption>c2</figcaption>end</figure>")
    '<figure><img><figcaption>c1</figcaption>middle<br><br>end</figure>'

    >>> fuse("<figure><img/><figcaption>c1</figcaption>end</figure>")
    '<figure><img><figcaption>c1</figcaption>end</figure>'
    """
    start, end = None, 0
    for idx, child in enumerate(figure):
        if start is None:
            if child.tag == "figcaption":
                start, end = idx, idx + 1
        elif child.tag == "figcaption" and not has_tail(figure[idx - 1]):
            end = idx + 1
        else:
            break
    # Dropping figcaptions that cannot be fused to avoid
    # having inconsistent figure
    for child in reversed(figure[end : len(figure)]):
        if child.tag == "figcaption":
            drop_tag_preserve_spacing(child, preserve_content=False)
    # Fuse the captions that we found can be fused
    if start is not None and end - start > 1:
        new_figcaption = wrap_children_slice(
            ChildrenSlice(figure, start, end), "figcaption"
        )
        for child in new_figcaption:
            drop_tag_preserve_spacing(child)


def clean_figcaptions_html(node: HtmlElement):
    """Simplifies figcapion html
    >>> html = fromstring("<div><figcaption><table><p><strong>hey</strong></p></table></figcaption></div>")
    >>> clean_figcaptions_html(html)
    >>> tostring(html).decode()
    '<div><figcaption><p><strong>hey</strong></p></figcaption></div>'
    """
    clean = _get_figure_caption_cleaner()
    for caption in node.xpath(".//figcaption"):
        clean(caption)


def remove_figures_without_content(doc: HtmlElement):
    """Removes figures that has no content apart of the figure caption. This
    can happen for some pages that inject the content with JS

    >>> remove = _test_fn(remove_figures_without_content)

    >>> remove("<div><figure><figcaption>fig</figcaption></figure></div>")
    '<div></div>'

    >>> remove("<div>hey<figure><figcaption>fig</figcaption></figure>John</div>")
    '<div>hey<br><br>John</div>'

    >>> remove("<div><figure>hey<figcaption>fig</figcaption></figure></div>")
    '<div><figure>hey<figcaption>fig</figcaption></figure></div>'

    >>> remove("<div><figure>hey<figcaption></figcaption></figure>hey</div>")
    '<div><figure>hey<figcaption></figcaption></figure>hey</div>'

    >>> remove("<div><figure><div></div><figcaption>fig</figcaption></figure></div>")
    '<div><figure><div></div><figcaption>fig</figcaption></figure></div>'

    >>> remove("<div><figure><div></div></figure></div>")
    '<div><figure><div></div></figure></div>'

    >>> remove("<figure><figcaption>fig</figcaption></figure>")
    '<figure><figcaption>fig</figcaption></figure>'
    """
    for figure in doc.xpath(".//figure"):
        non_figcaption = [child for child in figure if child.tag != "figcaption"]
        # Useful for single figcaption with tail case
        with_tail = len(figure) > 0 and has_tail(figure[0])
        has_childs = len(non_figcaption) > 0
        if not has_childs and not has_text(figure) and figure != doc and not with_tail:
            drop_tag_preserve_spacing(figure, preserve_content=False)


def clean_double_br_above_figcaption(doc: HtmlElement):
    """Some weird cases like when figure is implemented with tables
    we can end having a double br before figcaptions. For example
    in this case
    ``<figure><td><img/></td><td><figcaption><td>caption</td></figcaption></figure>``
    the clean_incomplete_structures will introduce the double br when
    cleaning the table elements. I have not a general solution for that so
    by now this function is used to mitigate this effect.

    >>> clean = _test_fn(clean_double_br_above_figcaption)
    >>> clean("<figure><br><br><figcaption>fig</figcaption></figure>")
    '<figure><figcaption>fig</figcaption></figure>'

    >>> clean("<figure><br><br>hey<figcaption>fig</figcaption></figure>")
    '<figure><br><br>hey<figcaption>fig</figcaption></figure>'

    >>> clean("<figure><br>hey<br><figcaption>fig</figcaption></figure>")
    '<figure><br>hey<br><figcaption>fig</figcaption></figure>'

    >>> clean("<figure>hey<br><br><figcaption>fig</figcaption></figure>")
    '<figure>hey<figcaption>fig</figcaption></figure>'

    >>> clean("<figure><figcaption>fig</figcaption></figure>")
    '<figure><figcaption>fig</figcaption></figure>'
    """
    for caption in doc.xpath(".//figcaption"):
        parent = caption.getparent()
        if parent is None:
            continue
        idx = parent.index(caption)
        if (
            idx >= 2
            and parent[idx - 1].tag == "br"
            and not has_tail(parent[idx - 1])
            and parent[idx - 2].tag == "br"
            and not has_tail(parent[idx - 2])
        ):
            parent[idx - 1].drop_tree()
            parent[idx - 2].drop_tree()
