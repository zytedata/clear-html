Changes
=======

0.5.0 (2025-10-24)
------------------

* Added support for Python 3.12-3.14.
* Dropped support for Python 3.8.
* Improved memory usage.
* Migrated the build system to ``hatchling``.
* Improved type hints.
* CI improvements.

0.4.1 (2024-04-30)
------------------

* Huge performance improvements on large documents.

0.4.0 (2023-08-29)
------------------

* Rename from ``clean-html`` to ``clear-html`` because of the PyPI name clash
  with ``CleanHTML``.

0.3.0 (2023-08-24)
------------------

* Make the project open-source.
* Fix and update type hints.

0.2.0 (2021-12-07)
------------------

* These functions now accept optional callables:
    * ``cleaned_node_to_text`` has ``text_extractor`` to extract text.
    * ``integrate_embeddings`` has ``preprocessor`` to preprocess whitelisted nodes


0.1.1 (2021-10-07)
------------------

* `cleaned_node_to_html` never return None anymore


0.1.0 (2021-09-17)
------------------

* Initial version.
