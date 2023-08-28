"""
 The goal of this module is to detect the embeddings from different
 providers and modify the
 HTML accordingly so that they can be integrated in the resultant
 HTML without change.
"""


from typing import Callable, Optional, Set

from lxml import etree
from lxml.html import HtmlElement

INSTAGRAM_CLASSES = ["instagram-media"]
TWITTER_CLASSES = ["twitter-tweet", "twitter-timeline", "twitter-moment"]
FACEBOOK_CLASSES = ["fb-post", "fb-video", "fb-comment-embed"]
ALL_WHITELISTING_CLASSES = set(INSTAGRAM_CLASSES + TWITTER_CLASSES + FACEBOOK_CLASSES)


def integrate_embeddings(
    doc: HtmlElement, preprocessor: Optional[Callable] = None
) -> Set[HtmlElement]:
    """Integrate all embeddings found in the provided document.
    Return a set of nodes that should be preserved 'as is' in the
    clean up process"""
    to_whitelist = _nodes_for_classes(doc, ALL_WHITELISTING_CLASSES)
    return _include_also_children(to_whitelist, preprocessor)


def _include_also_children(
    to_whitelist: Set[HtmlElement], preprocessor: Optional[Callable] = None
) -> Set[HtmlElement]:
    """Include all children to the whitelist with an optional ``preprocessor``
    Callable that is applied to all elements in the ``to_whitelist`` input.
    """
    if preprocessor:
        for el in to_whitelist:
            preprocessor(el)
    return _include_subtree(to_whitelist)


def _include_subtree(nodes: Set) -> Set[HtmlElement]:
    """Includes all nodes in subtrees of nodes in the set"""
    return {sub_node for node in nodes for sub_node in node.iter()}


def _nodes_for_classes(doc: HtmlElement, classes: Set[str]) -> Set[HtmlElement]:
    """Return a set with nodes having any of the classes in the list"""
    whitelisted: Set[HtmlElement] = set()
    for action, element in etree.iterwalk(doc, events=("start",)):
        assert isinstance(element, HtmlElement)  # always true in "start" events
        for cls in element.classes:
            if cls in classes:
                whitelisted.add(element)
                break
    return whitelisted
