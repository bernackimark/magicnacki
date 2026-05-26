from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from models.events_all import StateBasedEvent
from ..choice_actions_all import TriassicEggChoice
from ..modifiers import OwnershipMod
from ..zone import Zone

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

class Steal(Effect):
    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """If the zone is going from battlefield to battlefield, then move_card() will not trigger"""
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        original_owner_id = int(target.owner_id)
        target.modifiers.items.append(OwnershipMod(s=source, new_owner_id=source.owner_id))
        target.turn_entered_for_owner = gs.turn_mgr
        if target.zone == Zone.BATTLEFIELD:
            gs.boards[original_owner_id].remove(target)
            gs.boards[source.owner_id].append(target)
        else:
            gs.move_card(target, self.new_zone, cause='steal')
        gs.event_mgr.emit(StateBasedEvent(), gs)

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
        gy = gs.graveyards[target][:]
        gs.graveyards[target].clear()
        for card in gy:
            gs.exile(card)

class HandToBoard(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.cast(source)


# --- CARD-SPECIFIC ---
class GraveRobbersAA(Effect):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)

class TimeElementalBounce(Effect):
    """... {2UU}, {T}: Return target unenchanted permanent to its owner's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.bounce(target)

class TriassicEgg(Effect):
    """Choose one:
    * You may put a creature card from your hand onto the battlefield.
    * Return target creature card from your graveyard to the battlefield."""
    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
        gs.action_stack.push(TriassicEggChoice(source.owner_id, gs, source), gs, False)
