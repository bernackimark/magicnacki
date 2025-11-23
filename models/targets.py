from dataclasses import dataclass
from typing import Optional


# THIS IS NOT CURRENTLY BEING USED
# the eventual intent is to gracefully handle the fact that a target may be a card or a player ... or None?

@dataclass
class Target:
    card: Optional["GameCard"] = None
    player_id: Optional[int] = None

    @property
    def is_player(self) -> bool:
        return self.player_id is not None

    @property
    def is_card(self) -> bool:
        return self.card is not None


def card_targets(gs, source, flt):
    return [Target(card=c) for c in flt(gs, source)]

def player_targets(player_ids):
    return [Target(player_id=i) for i in player_ids]

