import json
import logging
from pathlib import Path
from typing import Dict

import attr


@attr.s(auto_attribs=True)
class BodyAnnotation:
    url: str
    raw_html: str
    expected_html: str


class BodyAnnotations(Dict[str, BodyAnnotation]):
    """
    Dict like structure that saves and reads from disk and that
    stores BodyAnnotation values for each item id.
    """

    @classmethod
    def load(cls, path: Path) -> "BodyAnnotations":
        if path.exists():
            with path.open("rt", encoding="utf8") as f:
                pages = json.load(f)
                return cls((k, BodyAnnotation(**v)) for k, v in pages.items())
        logging.info(
            f"Body annotations file does not exist in {path}. "
            f"Loading empty annotations"
        )
        return cls({})

    def save(self, path: Path):
        as_dict = {id: attr.asdict(ann) for id, ann in self.items()}
        path.write_text(
            json.dumps(as_dict, sort_keys=True, ensure_ascii=False, indent=4),
            encoding="utf8",
        )
