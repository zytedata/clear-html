"""
Article body formatting module. Cleanup, normalize and format.

Part of the cleanup process involves removing tags but keeping the content.
There are two kinds of tags in HTML. The inline ones are used within the
paragraphs (i.e. strong or em) and when removed but keeping the content no
extra spacing should be included. For example: ``<p>I would like to visit
<span class="location">Spain</span> this summer</p>`` should be simplified
in the clean up process to ``<p>I would like to visit Spain this summer</p>``

By the other side, block tags (i.e. div) are used to divide blocks of content.
And their behaviour should be the same than paragraphs. For example,
the cleaning process should convert
``<div>This is first paragraph</div><div>And this second</div>``
to
``<p>This is first paragraph</p><p>And this second</p>``
The body cleaner is doing that in two stages. The first one is separating
these two sentences by double br:
``This is first paragraph<br><br>And this second.``
In a second stage the double or more consecutive BRs are converted into the
final paragraphs (it is a good normalization practise even if they were already
part of original page).

The logic regarding when to introduce a double br is not always as simple as
these shown in the examples before, but the general idea is that content
in different blocks should be separated by at least one block tag or
by double br if there is a need to remove the block tags and because of that
the consecutive content would not be then separated by a block tag anymore.

Main approach is to update the document inline, without doing copies.

Steps:
  - Look for particular embeddings, adapt html and freeze concerning nodes
  - Remove tags not accepted in our simplified html, but keeping spacing
    information. This is done by introducing double br in some cases.
  - Apply some rules to normalize html: headings, figures, clean
    incomplete structures.
  - Convert consecutive chunks of text into paragraphs (this remove the
    double br introduced in parts of the process).
  - Ensure that not block tags are inside inline tags (this is not allowed).
  - Finally html is formatted a little bit to have a good looking.
"""
from clear_html.formatted_text.main import clean_doc  # noqa: F401
