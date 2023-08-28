from typing import cast

import pytest
from lxml.html import HtmlElement, fromstring, tostring

from clear_html.formatted_text.figures import enclose_media_within_figure
from clear_html.formatted_text.main import _get_default_cleaner, paragraphy
from clear_html.formatted_text.utils import drop_tag_preserve_spacing


@pytest.mark.parametrize(
    ["html", "expected_output"],
    [
        ["<article></article>", "<article></article>"],
        ["<article><em></em></article>", "<article><p><em></em></p></article>"],
        ["<article>text</article>", "<article><p>text</p></article>"],
        ["<article>h<br></article>", "<article><p>h<br></p></article>"],
        ["<article>h<br><br></article>", "<article><p>h</p></article>"],
        ["<article>h<br><br>   </article>", "<article><p>h</p></article>"],
        ["<article>h<br><br>e</article>", "<article><p>h</p><p>e</p></article>"],
        ["<article>h<br><br><br>e</article>", "<article><p>h</p><p>e</p></article>"],
        ["<article><br><br>h</article>", "<article><p>h</p></article>"],
        [
            "<article>h<br><br>e<br><br>l<br>lo</article>",
            "<article><p>h</p><p>e</p><p>l<br>lo</p></article>",
        ],
        [
            "<article><em>h</em><br><br><em>e</em></article>",
            "<article><p><em>h</em></p><p><em>e</em></p></article>",
        ],
        [
            "<article><em>h</em>e<br><br>l<em>l</em></article>",
            "<article><p><em>h</em>e</p><p>l<em>l</em></p></article>",
        ],
        ["<article><p>h<br><br></p></article>", "<article><p>h<br><br></p></article>"],
        [
            "<article>t<em>e</em>x<table><thead><tr><td>tbl</td></tr></thead></table>t<em>e</em>xt</article>",
            "<article><p>t<em>e</em>x</p><table><thead><tr><td>tbl</td></tr></thead></table><p>t<em>e</em>xt</p></article>",
        ],
    ],
)
def test_paragraphy(html, expected_output):
    root = fromstring(html)
    paragraphy(root)
    assert tostring(root, encoding="unicode") == expected_output


@pytest.mark.parametrize(
    ["html", "expected_output"],
    [
        [
            '<article><img src="img1.jpg"></article>',
            '<article><figure><img src="img1.jpg"></figure></article>',
        ],
        [
            '<article><iframe src="img1.jpg"></iframe></article>',
            '<article><figure><iframe src="img1.jpg"></iframe></figure></article>',
        ],
        [
            '<article><figure><img src="img1.jpg"></figure></article>',
            '<article><figure><img src="img1.jpg"></figure></article>',
        ],
        [
            '<article><a><img src="img1.jpg"></a></article>',
            '<article><figure><a><img src="img1.jpg"></a></figure></article>',
        ],
    ],
)
def test_enclose_media_within_figures(html, expected_output):
    root = fromstring(html)
    enclose_media_within_figure(root)
    assert tostring(root, encoding="unicode") == expected_output


@pytest.mark.parametrize(
    ["html", "expected_output"],
    [
        [
            "<html><body>pre<div>text</div>post</body></html>",
            "<div>pre<br><br>text<br><br>post</div>",
        ],
        [
            "<div>pre<div>text <strong>more</strong></div>post</div>",
            "<div>pre<br><br>text <strong>more</strong><br><br>post</div>",
        ],
        [
            "<div><div>pre</div><div>text <strong>more</strong></div></div>",
            "<div>pre<br><br>text <strong>more</strong></div>",
        ],
        [
            "<div><div>text <strong>more</strong></div>post</div>",
            "<div>text <strong>more</strong><br><br>post</div>",
        ],
        [
            "<div>pre<br><br><div>text <strong>more</strong></div>post</div>",
            "<div>pre<br><br>text <strong>more</strong><br><br>post</div>",
        ],
        [
            "<div><br>he<br><div>text</div><br><br>post</div>",
            "<div><br>he<br><br><br>text<br><br>post</div>",
        ],
        ["<div><div>text</div><div>post</div></div>", "<div>text<br><br>post</div>"],
        [
            "<div>pre<div><div>text</div></div><div>post</div></div>",
            "<div>pre<br><br>text<br><br>post</div>",
        ],
        [
            "<div>pre <span>text</span><div>post</div></div>",
            "<div>pre text<br><br>post</div>",
        ],
        [
            '<div><img src="img.jpg" data-src="img.jpg" to-filter="b"></div>',
            '<div><img src="img.jpg" data-src="img.jpg"></div>',
        ],
        [
            "<div>pre<form><div>text</div></form>post</div>",
            "<div>pre<br><br>text<br><br>post</div>",
        ],
        [
            "<div>A<div>div<div>structure</div>here</div>!</div>",
            "<div>A<br><br>div<br><br>structure<br><br>here<br><br>!</div>",
        ],
        [
            "<div>Another<div>div</div>structure<div>here</div>!</div>",
            "<div>Another<br><br>div<br><br>structure<br><br>here<br><br>!</div>",
        ],
        ["<div><div><div><div>Hey!</div></div></div></div>", "<div>Hey!</div>"],
        [
            "<div>Hurra<div><div><div>Hey!</div></div></div>Hurra</div>",
            "<div>Hurra<br><br>Hey!<br><br>Hurra</div>",
        ],
        [
            "<div>A<span> span<span> structure</span> here</span>!</div>",
            "<div>A span structure here!</div>",
        ],
        [
            "<div><span><span><span></span></span></span><div></div></div>",
            "<div></div>",
        ],
        [
            "<div><span><span><span></span></span></span><div>Hey!</div></div>",
            "<div>Hey!</div>",
        ],
        [
            "<div><span><span><span>Double</span></span></span><div>Hey!</div></div>",
            "<div>Double<br><br>Hey!</div>",
        ],
        [
            "<div><div><div><span>Updated every <span>60</span> sg</span></div>Per minute</div></div>",
            "<div>Updated every 60 sg<br><br>Per minute</div>",
        ],
    ],
)
def test_body_cleaner(html, expected_output):
    root = fromstring(html)
    cleaner = _get_default_cleaner()
    cleaner(root)
    assert tostring(root, encoding="unicode") == expected_output


@pytest.mark.parametrize(
    ["html", "selector", "expected_output"],
    [
        [
            "<div>pre<p>text</p>post</div>",
            "..//p",
            "<div>pre<br><br>text<br><br>post</div>",
        ],
        [
            "<div>pre<p>text <strong>more</strong></p>post</div>",
            "..//p",
            "<div>pre<br><br>text <strong>more</strong><br><br>post</div>",
        ],
        [
            "<div><p>pre</p><p>text <strong>more</strong></p></div>",
            "..//p[2]",
            "<div><p>pre</p>text <strong>more</strong></div>",
        ],
        [
            "<div><p>text <strong>more</strong></p>post</div>",
            "..//p",
            "<div>text <strong>more</strong><br><br>post</div>",
        ],
        [
            "<div>pre<br><br><p>text <strong>more</strong></p>post</div>",
            "..//p",
            "<div>pre<br><br>text <strong>more</strong><br><br>post</div>",
        ],
        [
            "<div><br>he<br><p>text</p><br><br>post</div>",
            "..//p",
            "<div><br>he<br><br><br>text<br><br>post</div>",
        ],
        ["<div><p>text</p><p>post</p></div>", "..//p", "<div>text<p>post</p></div>"],
        [
            "<div>pre<invented> text </invented>post</div>",
            "..//invented",
            "<div>pre text post</div>",
        ],
    ],
)
def test_drop_tag_preserve_spacing(
    html: str, selector: str, expected_output: str
) -> None:
    node: HtmlElement = fromstring(html)
    drop_tag_preserve_spacing(cast(HtmlElement, node.find(selector)))
    assert tostring(node, encoding="unicode") == expected_output


@pytest.mark.parametrize(
    ["html", "selector", "expected_output"],
    [
        ["<div>pre<p>text</p>post</div>", "..//p", "<div>pre<br><br>post</div>"],
        [
            "<div>pre<p>text <strong>more</strong></p>post</div>",
            "..//p",
            "<div>pre<br><br>post</div>",
        ],
        [
            "<div><p>pre</p><p>text <strong>more</strong></p></div>",
            "..//p[2]",
            "<div><p>pre</p></div>",
        ],
        [
            "<div><p>text <strong>more</strong></p>post</div>",
            "..//p",
            "<div>post</div>",
        ],
        [
            "<div>pre<br><br><p>text <strong>more</strong></p>post</div>",
            "..//p",
            "<div>pre<br><br>post</div>",
        ],
        [
            "<div><br>he<br><p>text</p><br><br>post</div>",
            "..//p",
            "<div><br>he<br><br><br>post</div>",
        ],
        ["<div><p>text</p><p>post</p></div>", "..//p", "<div><p>post</p></div>"],
        [
            "<div>pre<invented> text </invented>post</div>",
            "..//invented",
            "<div>prepost</div>",
        ],
    ],
)
def test_drop_tag_preserve_spacing_but_not_content(
    html: str, selector: str, expected_output: str
) -> None:
    node: HtmlElement = fromstring(html)
    drop_tag_preserve_spacing(
        cast(HtmlElement, node.find(selector)), preserve_content=False
    )
    assert tostring(node, encoding="unicode") == expected_output
