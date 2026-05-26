from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base import Effect
from models.events_all import UntapCardEvent
from models.modifiers import PTMod, OwnershipMod
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class UntapRemovesPumpFromAnotherCard(Effect):
    """If an effect targeted another card and its duration was for as long as the source is tapped,
    we untap here by polling all cards in play and seeing if they were given a Pump by this source"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: UntapCardEvent):
        for c in gs.card_filter.in_play().result():
            for mod in list(c.modifiers):
                if mod.source is s and isinstance(mod, PTMod):
                    event.card.modifiers.items.remove(mod)


class ReturnToOwnerOnUntap(Effect):
    """Ownership by virtue of an aura or the source being on the battlefield will auto-remove the mod upon LTB;
    This effect removes an ownership mod on any card the source was placed & xfers the stolen GameCard across boards"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapCardEvent):
        if source is not event.card:
            return
        for c in gs.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod):
                    c.modifiers.remove(mod)
                    gs.boards[source.owner_id].remove(c)
                    gs.boards[flip(source.owner_id)].append(c)
                    break
