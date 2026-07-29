from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from models.effects.base import Listener
from models.events_all import StateBasedEvent, Event
from models.modifiers import OwnershipMod
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

class GlobalSac(Listener):
    """Upon each StateBasedEvent, sacrifice cards that cannot be there based on the board state"""
    listens_to = StateBasedEvent

    def __init__(self, affected_card_func: Callable, condition: Callable = None):
        self.affected_card_func = affected_card_func
        self.condition = condition

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        affected_cards = self.affected_card_func(gs, source)
        if not isinstance(affected_cards, list):
            affected_cards = [affected_cards]
        if self.condition is None or self.condition(gs, source):
            for card in affected_cards:
                gs.pile_mgr.destroy(card, allow_regeneration=False)

class JihadSac(Listener):
    """When the chosen player controls no nontoken permanents of the chosen color, sacrifice this enchantment"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        declared_color = source.extras.get('color_declaration')
        opp = flip(source.owner_id)
        if not gs.card_filter.on_player_board(opp).by_color(declared_color).non_token().permanents().result():
            gs.pile_mgr.destroy(source, allow_regeneration=False)

class OldManOfTheSeaPowerCheck(Listener):
    """Gain control of target creature with power <= OMOTS's power for as long as ... t
    arget's power remains <= OMOTS's power."""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.modifiers.get(OwnershipMod, reverse=True):
                if mod.s is source:
                    print('AAA', source, source.power, c.power)
                    if source.power > c.power:
                        print('YYY')
                        c.modifiers.remove(mod)
                        gs.pile_mgr.boards[source.owner_id].remove(c)
                        gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                        return
