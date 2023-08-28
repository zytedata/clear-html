from typing import AbstractSet, Optional

from lxml import etree
from lxml.html import HtmlElement, defs
from lxml.html.clean import Cleaner

from clear_html.formatted_text.utils import drop_tag_preserve_spacing
from clear_html.lxml_utils import iter_deep_first_post_order


class BodyCleaner(Cleaner):
    """Cleaner based on lxml Cleaner but with some modifications.

    First is that the following options that ask for tag removal but
    keeping content will be ignored: ``page_structure``, ``embedded``,
    ``forms``, ``annoying_tags``. Only tags not killed by the rest of options
    and that are not present in allow_tags will be dropped keeping content.

    ``nodes_whitelist``:
        A set of nodes to ignore in the cleaning up. They are both ignored
        in terms of element deletion or attribute cleaning.

    ``allow_data_attrs``:
        If true, attributes data-* are not removed

    ``allow_tags``:
        Drop tags not in this set (keeping content). The cleaner try to do
        its best to respect text separation by inserting double br tags in
        some cases.
    """

    def __init__(
        self,
        nodes_whitelist: Optional[AbstractSet[HtmlElement]] = None,
        allow_data_attrs: bool = True,
        allow_tags=None,
        **kw,
    ):
        # Short-circuit the safe_attrs to be able to provide a smarter filtering
        self._body_safe_attrs = kw.pop("safe_attrs", defs.safe_attrs)
        self._body_safe_attrs_only = kw.pop("safe_attrs_only", True)
        kw["safe_attrs_only"] = False
        self._nodes_whitelist = nodes_whitelist or set()
        self._allow_data_attrs = allow_data_attrs
        self._allow_tags = allow_tags

        # Ignoring the options for tags removal, as all allowed removal
        # will be done within this class
        for option in ["page_structure", "embedded", "forms", "annoying_tags"]:
            kw[option] = False
        super().__init__(**kw)

    def __call__(self, doc: HtmlElement):  # type: ignore[override]
        super().__call__(doc)
        if self._body_safe_attrs_only:
            safe_attrs = self._body_safe_attrs
            for el in doc.iter(etree.Element):
                if el in self._nodes_whitelist:
                    continue
                attrib = el.attrib
                for aname in attrib.keys():
                    if self._allow_data_attrs and aname.startswith("data-"):
                        continue
                    if aname not in safe_attrs:
                        del attrib[aname]

        # Removal of not allowed tags, but adding double br in some cases
        # to respect the block separation
        if self._allow_tags:
            to_remove = []
            for el in iter_deep_first_post_order(doc):
                if el.tag not in self._allow_tags and not self.allow_element(el):
                    to_remove.append(el)
            if to_remove:
                if to_remove[-1] is doc:
                    # Root element cannot be removed
                    el = to_remove.pop(-1)
                    el.tag = "div"
                    el.attrib.clear()
                for el in to_remove:
                    drop_tag_preserve_spacing(el)

    def allow_element(self, el):
        if el in self._nodes_whitelist:
            return True
        return super().allow_element(el)
