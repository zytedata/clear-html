from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import attr

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True)
class BodyAnnotation:
    url: str
    raw_html: str
    expected_html: str


class BodyAnnotations(dict[str, BodyAnnotation]):
    """
    Dict like structure that saves and reads from disk and that
    stores BodyAnnotation values for each item id.
    """

    @classmethod
    def load(cls, path: Path) -> BodyAnnotations:
        if path.exists():
            with path.open("rt", encoding="utf8") as f:
                pages = json.load(f)
                return cls((k, BodyAnnotation(**v)) for k, v in pages.items())
        logger.info(
            f"Body annotations file does not exist in {path}. Loading empty annotations"
        )
        return cls({})

    def save(self, path: Path) -> None:
        as_dict = {id_: attr.asdict(ann) for id_, ann in self.items()}
        path.write_text(
            json.dumps(as_dict, sort_keys=True, ensure_ascii=False, indent=4),
            encoding="utf8",
        )
