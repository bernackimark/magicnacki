from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState
    from models.effects.base import EffSpec

@dataclass
class Emblem:
    player_id: int
    source: GameCard
    eff_spec: EffSpec
    expires: str | None = None

class EmblemManager:
    def __init__(self, gs: GameState):
        self._gs: GameState = gs
        self._emblems: list[Emblem] = []

    @property
    def emblems(self) -> list[Emblem | None]:
        return self._emblems

    def add_emblem(self, e: Emblem) -> None:
        self._emblems.append(e)

    def remove_emblem(self, e: Emblem) -> None:
        self._emblems = [em for em in self._emblems if em != e]

    def clear_eots(self):
        self._emblems = [em for em in self._emblems if em.expires != 'EOT']
