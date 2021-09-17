import parsel
from lxml.html import HtmlElement


def string_to_html_element(html: str) -> HtmlElement:
    return parsel.Selector(html).root
