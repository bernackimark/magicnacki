from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.events_all import StateBasedEvent, CastResolvedEvent
from models.zone import Zone

@dataclass
class CastPermanentAction(Action):
    """Used for cards (all would be permanents) that have no casting spell"""
    source: GameCard

    def __repr__(self) -> str:
        return f"Cast {self.source.props.name}"

    def play(self) -> None:
        self.gs.mana_pools[self.player_idx].pay(self.source.casting_cost)

        print(f"Successfully cast {self.source.props.name}")
        self.gs.pile_mgr.move_card(self.source, Zone.BATTLEFIELD, cause='cast')
        self.gs.event_mgr.emit(CastResolvedEvent(self.source, self.source.orig_owner_id, None), self.gs)

        if self.source.is_land:
            self.gs.turn_mgr.has_played_land = True

        from models.effects.base import Listener
        for eff_spec in self.source.abilities:
            if isinstance(eff_spec.effect, Listener):
                self.gs.event_mgr.register(eff_spec.effect, self.source)
                print(f"Registered listener for {self.source.props.name}: {eff_spec.effect}")

        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)
