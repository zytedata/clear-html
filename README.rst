==========
clean-html
==========

.. image:: https://circleci.com/gh/zytedata/clean-html/tree/master.svg?style=shield&circle-token=893cc11762c086c550a812d6c8bc3e1a1c6f25cb
    :target: https://circleci.com/gh/zytedata/clean-html/tree/master

Clean and normalize HTML. Preserve embeddings (e.g. Twitter, Instagram, etc)

.. contents::

Quick start
***********

Installation
============

Install the library with pip::

    pip install clean-html

Usage
=====

Example usage with lxml:

.. code-block:: python

    from lxml.html import fromstring
    from clean_html import clean_node, cleaned_node_to_html

    html="""
            <div style="color:blue" id="main_content">
                Some text to be
                <div>cleaned up!</div>
            </div>
         """
    node = fromstring(html)
    cleaned_node = clean_node(node)
    cleaned_html = cleaned_node_to_html(cleaned_node)
    print(cleaned_html)


Example usage with Parsel:

.. code-block:: python

    from parsel import Selector
    from clean_html import clean_node, cleaned_node_to_html

    selector = Selector(text="""<html>
                                <body>
                                    <h1>Hello!</h1>
                                    <div style="color:blue" id="main_content">
                                        Some text to be
                                        <div>cleaned up!</div>
                                    </div>
                                </body>
                                </html>""")
    selector = selector.css("#main_content")
    cleaned_node = clean_node(selector[0].root)
    cleaned_html = cleaned_node_to_html(cleaned_node)
    print(cleaned_html)

Both of the different approaches above would print the following:

.. code-block:: HTML

    <article>

    <p>Some text to be</p>

    <p>cleaned up!</p>

    </article>


Other interesting functions:

* ``cleaned_node_to_text``: convert the cleaned node to plain text
* ``formatted_text.clean_doc``: low level method to control more aspects
  of the cleaning up
