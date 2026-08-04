from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.events_all import StateBasedEvent, CastResolvedEvent, StackAdditionEvent
from models.zone import Zone

@dataclass
class CastWithNoSpellEffect(Action):
    """Used for casting non-land permanents with no casting spell
    that do not need an ability pipeline but do need to be pushed onto the stack"""
    source: GameCard

    def __repr__(self):
        return f"Cast {self.source.props.name}"

    def play(self) -> None:
        self.gs.mana_pools[self.player_idx].pay(self.source.casting_cost)
        action = CastPermanentAction(self.source.owner_id, self.gs, self.source)
        self.gs.action_stack.push(action, self.gs)


@dataclass
class CastPermanentAction(Action):
    """Used for cards (all would be permanents), including lands, that have no casting spell"""
    source: GameCard

    def __repr__(self) -> str:
        return f"Cast {self.source.props.name}"

    def play(self) -> None:
        print(f"Successfully cast {self.source.props.name}")
        self.gs.pile_mgr.move_card(self.source, Zone.BATTLEFIELD, cause='cast')
        self.gs.event_mgr.emit(CastResolvedEvent(self.source, self.source.orig_owner_id, None))

        if self.source.is_land:
            self.gs.turn_mgr.has_played_land = True

        self.gs.event_mgr.register_card(self.source)
        self.gs.event_mgr.emit(StateBasedEvent())
        self.finish()

    @property
    def total_mana_cost(self) -> str:
        return self.source.casting_cost
