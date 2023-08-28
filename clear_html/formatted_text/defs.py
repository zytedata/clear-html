from lxml.html import defs

ALLOWED_ATTRIBUTES = frozenset(
    [
        "alt",
        "cite",
        "colspan",
        "datetime",
        "dir",
        "href",
        "label",
        "rowspan",
        "src",
        "srcset",
        "sizes",
        "start",
        "title",
        "type",
        "value",
        "vspace",
    ]
)
CAN_HAVE_TEXT_TAGS = frozenset(
    [
        "a",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "aside",
        "blockquote",
        "code",
        "pre",
        "li",
        "td",
        "dt",
        "dd",
        "b",
        "strong",
        "i",
        "em",
        "u",
        "sup",
        "sub",
        "s",
        "figcaption",
        "cite",
    ]
)
TOP_LEVEL_TAGS = frozenset(
    [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "figure",
        "aside",
        "blockquote",
        "code",
        "pre",
        "ul",
        "ol",
        "table",
        "dl",
    ]
)
INLINE_TAGS = frozenset(["br", "strong", "em", "u", "sup", "sub", "a", "s", "cite"])
FIGURE_CONTENT_TAGS = frozenset(["img", "video", "audio", "iframe", "embed", "object"])
WRAPPED_WITH_FIGURE = frozenset(FIGURE_CONTENT_TAGS | {"figcation"})
EMBEDDING_TAGS = frozenset(["video", "audio", "source", "iframe", "embed", "object"])
TABLE_TAGS = frozenset(["table", "thead", "tfoot", "tbody", "th", "tr", "td"])
DEF_LIST_TAGS = frozenset(["dl", "dt", "dd"])
LIST_TAGS = frozenset(["ul", "ol", "li"])
CAN_BE_EMPTY = frozenset({"img", "br", "dt", "dd", "td"} | EMBEDDING_TAGS)
TRANSPARENT_CONTENT = frozenset({"a"})
ALLOWED_TAGS = frozenset(
    CAN_HAVE_TEXT_TAGS
    | TOP_LEVEL_TAGS
    | INLINE_TAGS
    | WRAPPED_WITH_FIGURE
    | TABLE_TAGS
    | DEF_LIST_TAGS
    | LIST_TAGS
    | EMBEDDING_TAGS
)
FIGURE_CAPTION_ALLOWED_TAGS = frozenset(
    {"figcaption", "a", "p", "b", "i"} | INLINE_TAGS
)
STRUCTURE_TAGS = frozenset(TABLE_TAGS | DEF_LIST_TAGS | LIST_TAGS)

# Tags in key must be descendant of at least one of the tags in the value
MUST_ANCESTORS_FOR_KEEP_CONTENT = dict(
    li=LIST_TAGS - {"li"},
    **dict(
        [(tag, {"table"}) for tag in TABLE_TAGS - {"table"}]
        + [(tag, {"dl"}) for tag in DEF_LIST_TAGS - {"dl"}]
    ),
)
MUST_ANCESTORS_FOR_KEEP_CONTENT_REVERSED = {
    root: descendant
    for descendant, root_set in sorted(MUST_ANCESTORS_FOR_KEEP_CONTENT.items())
    for root in sorted(root_set)
}
MUST_ANCESTORS_FOR_DROP_CONTENT = dict(figcaption={"figure"})

# As defined in HTML5 spec: https://html.spec.whatwg.org/#phrasing-content
# and also including some HTML 4 ones defined in lxml
PHRASING_CONTENT = frozenset(
    {
        "a",
        "abbr",
        "audio",
        "b",
        "bdi",
        "bdo",
        "br",
        "button",
        "canvas",
        "cite",
        "code",
        "data",
        "datalist",
        "del",
        "dfn",
        "em",
        "embed",
        "i",
        "iframe",
        "img",
        "input",
        "ins",
        "kbd",
        "label",
        "link",
        "map",
        "mark",
        "math",
        "meta",
        "meter",
        "noscript",
        "object",
        "output",
        "picture",
        "progress",
        "q",
        "ruby",
        "s",
        "samp",
        "script",
        "select",
        "slot",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "svg",
        "template",
        "textarea",
        "time",
        "u",
        "var",
        "video",
        "wbr",
    }
    | defs.special_inline_tags
)

# List with all known html tags by the module
HTML_UNIVERSE_TAGS = frozenset(defs.tags | PHRASING_CONTENT | ALLOWED_TAGS)

# b is more or less the same than strong, and other cases.
# See https://stackoverflow.com/questions/271743/whats-the-difference-between-b-and-strong-i-and-em
TAG_TRANSLATIONS = dict(
    b="strong",
    i="em",
    tt="code",
)

# Not yet used. Keeping here the trusted domains found during the development of
# the module. At some point this list will be used to filter embeddings so
# that only embeddings from these domains are allowed.
HOST_WHITELIST = frozenset(
    [
        "youtube.com",
        "instagram.com",
    ]
)
CONTENT_EVEN_IF_EMPTY = frozenset({"img"} | EMBEDDING_TAGS)
