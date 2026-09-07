from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any


class PresentationReqType(StrEnum):
    DECLARE = auto()  # ex: declare a color, a card sub_type
    SEARCH_LIBRARY = auto()  # searching & selecting a card(s); ex: tutor
    VIEW_LIBRARY = auto()  # read-only viewing of library; ex: visions


@dataclass
class PresentationRequest:
    """Present something to player(s) that outside of the standard board (card reveal, declaration, search a pile)"""
    viewer_id: int
    type_: PresentationReqType
    payload: dict[str, Any]
