from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.effects.base import Listener
from models.events_all import ZoneChangeEvent
from models.constants import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class LandEquilibrium(Listener):
    """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
    that player instead puts that land onto the battlefield then sacrifices a land of their choice"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id == event.card.owner_id or 'Land' not in event.card.card_types:
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if len(opp_lands) < your_land_cnt:
            return
        options = [CO(f'Sac {land}', lambda: gs.pile_mgr.sacrifice(land)) for land in opp_lands]
        gs.choice_mgr.queue(ChoiceAction(options))

class TawnossCoffinLTB(Listener):
    """When this artifact LTB, return its exiled card to the battlefield tapped with the noted number &
     kind of counters on it and re-attach all auras.
     Note: all of this code is repeated in TawnossCoffinUntap"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        if event.card is not source or event.to_zone == Zone.BATTLEFIELD:
            return
        exiled_card: GameCard = source.extras.get('exiled_card')
        deep_copy: GameCard = source.extras.get('exiled_card_deep_copy')
        exiled_card.tap()
        for ctr in deep_copy.counters:
            exiled_card.counters.add_counter(ctr)
        for aura in deep_copy.modifiers.items:
            if isinstance(aura, GameCard):
                exiled_card.modifiers.append(aura)
