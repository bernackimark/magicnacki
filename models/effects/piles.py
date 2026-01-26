from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

class GraveyardToExile(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        card = gs.remove_from_any_graveyard(target)
        gs.send_to_exile(card)

class GraveyardToExileInItsEntirety(Effect):
    """Moves all cards from target player's graveyard to that same player's exile"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gy = gs.graveyards[source.orig_owner_id][:]
        gs.graveyards[source.orig_owner_id].clear()
        for card in gy:
            gs.send_to_exile(card)

class GraveyardToHand(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        card = gs.remove_from_your_graveyard(target, source.orig_owner_id)
        gs.add_to_hand(card, source.orig_owner_id)

class HandToBoard(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.hands[source.orig_owner_id].cards.remove(target)
        gs.boards[source.orig_owner_id].play_to_board(target)

class GraveRobbersAA(Effect):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.increment_life(source.orig_owner_id, 2)


def graveyard_to_board():
    """Return target from your graveyard to your board"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            card = gs.remove_from_your_graveyard(target, source.orig_owner_id)
            gs.boards[source.orig_owner_id].play_to_board(card)
    return E()


def graveyard_to_hand():
    """Return target from your graveyard to your hand"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            card = gs.remove_from_your_graveyard(target, source.orig_owner_id)
            gs.add_to_hand(card, source.orig_owner_id)
    return E()


def boomerang_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                board = gs.boards[target.orig_owner_id]
                board.remove_from_board(target)
                gs.return_to_hand(target)
    return E()


def unsummon_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                board = gs.boards[target.orig_owner_id]
                board.remove_from_board(target)
                gs.return_to_hand(target)
    return E()
