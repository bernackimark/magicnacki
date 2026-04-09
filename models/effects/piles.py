from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from models.utils import flip
from models.events_all import ZoneChangeEvent, UpkeepEvent, Event, StateBasedEvent, UntapCardEvent
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
        if target.zone == Zone.BATTLEFIELD:
            gs.boards[original_owner_id].remove(target)
            gs.boards[source.owner_id].append(target)
        else:
            gs.move_card(target, self.new_zone, cause='steal')
        gs.event_mgr.emit(StateBasedEvent(), gs)

class ReturnToOwnerOnLTB(Effect):
    """Although the OnwershipMod will be removed upon LTB; need to transfer the stolen GameCard across boards"""
    listens_to = ZoneChangeEvent

    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        for c in gs.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod):
                    gs.boards[source.owner_id].remove(c)
                    gs.boards[flip(source.owner_id)].append(c)

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
        print(source, event, f'The host {event.card.host} belongs to player #{event.card.host.owner_id if event.card.host else "no host"}')
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        host = event.card.host
        Steal().resolve(gs, source, host)
        print('I think I returned control to', flip(host.owner_id))


# --- CARD-SPECIFIC ---
class GhazbanOgre(Effect):
    """At your upkeep, if a player has more life than each other player,
    the player with the most life gains control of this creature (assuming "your" = the current controller)"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: Event):
        if gs.player_turn_idx != source.owner_id:
            return
        if len(set(gs.score_mgr.life)) == 1:
            return
        most_life_player_idx = max(range(len(gs.score_mgr.life)), key=lambda i: gs.score_mgr.life[i])
        if most_life_player_idx != source.owner_id:
            Steal().resolve(gs, source, source)

class GraveRobbersAA(Effect):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.score_mgr.increment_life(source.orig_owner_id, 2, source, gs)

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
