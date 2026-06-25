from dataclasses import dataclass
from typing import Any


@dataclass
class PresentationRequest:
    viewer_id: int
    type_: str
    payload: dict[str, Any]
