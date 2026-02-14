from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from utils import flip
from .identity import NoLongerACreature
from ..events.base import Event
from ..events.events_all import ZoneChangeEvent, UpkeepEvent
from ..zone import Zone

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

class AnimatorCardLeaves(Effect):
    """The host was turned from a non-creature into a creature; must return it to a non-creature state on leave"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        host = event.card.attached_to
        NoLongerACreature().resolve(gs, source, host)

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
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        print(target, target.owner_id)
        print(gs.boards[target.owner_id])
        gs.boards[target.owner_id].remove(target)
        gs.boards[flip(target.owner_id)].append(target)
        target.owner_id = flip(target.owner_id)

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

class StealCardLeaves(Effect):
    """You control enchanted creature; must return if Control Magic leaves board"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        print(source, event, f'The host {event.card.attached_to} belongs to player #{event.card.attached_to.owner_id if event.card.attached_to else "no host"}')
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        host = event.card.attached_to
        Steal().resolve(gs, source, host)
        print('I think I returned control to', flip(host.owner_id))

class GhazbanOgre(Effect):
    """At your upkeep, if a player has more life than each other player,
    the player with the most life gains control of this creature (assuming "your" = the current controller)"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: Event):
        if gs.player_turn_idx != source.owner_id:
            return
        if len(set(gs.life)) == 1:
            return
        most_life_player_idx = max(range(len(gs.life)), key=lambda i: gs.life[i])
        if most_life_player_idx != source.owner_id:
            Steal().resolve(gs, source, source)

class GraveRobbersAA(Effect):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.increment_life(source.orig_owner_id, 2)
