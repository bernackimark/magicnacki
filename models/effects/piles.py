from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

class Bounce(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.bounce(target)

class Reanimate(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.reanimate(target)

class GraveyardToExile(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.exile(target)

class GraveyardToExileInItsEntirety(Effect):
    """Moves all cards from target player's graveyard to that same player's exile"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gy = gs.graveyards[source.orig_owner_id][:]
        gs.graveyards[source.orig_owner_id].clear()
        for card in gy:
            gs.exile(card)

class HandToBoard(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.cast(source)

class GraveRobbersAA(Effect):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.increment_life(source.orig_owner_id, 2)
