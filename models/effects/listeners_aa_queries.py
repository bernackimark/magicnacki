from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from models.effects.resolvers_generic import Regenerate
from models.events_all import ActivatedAbilitiesQueryEvent
from models.game_card.card_filter_funcs import CF

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Listener, Activated

"""
Called when GameState seeks out a card's activated abilities.
Although most are printed on the card, some may come from other sources.
(ex: zombie-master: Other Zombies have '{B}: Regenerate this permanent.' -> 
[AAApplies(CF.other_zombies(), Activated('B', Regenerate(), CF.self()))]
"""


class AAApplies(Listener):
    """If card is in applies_to_func, add the ActivatedAbility to the query"""
    listens_to = ActivatedAbilitiesQueryEvent

    def __init__(self, applies_to_func: Callable, added_aa: Activated):
        self.applies_to_func = applies_to_func
        self.added_aa = added_aa

    def on_event(self, gs: GameState, source: GameCard, event: ActivatedAbilitiesQueryEvent) -> None:
        applies_to = self.applies_to_func(gs, source)
        if not isinstance(applies_to, list):
            applies_to = [applies_to]
        if event.card in applies_to:
            event.abilities.append(self.added_aa)
