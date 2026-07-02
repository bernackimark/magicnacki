from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.effects.base import Listener
from models.events_all import LifeLossEvent, CastResolvedEvent, MainPhaseEvent, Event
from models.utils import flip


# --- CAST RESOLVED EVENT ---
class IchneumonDruid(Listener):
    """Whenever an opponent casts their non-first instant spell that turn, ID deals 4 damage to that player."""
    listens_to = CastResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> None:
        opp = flip(source.owner_id)
        instants_cast_in_turn = len([e for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, CastResolvedEvent)
                                    if e.owner_id == opp and 'Instant' in e.card.card_types])
        if instants_cast_in_turn > 1:
            gs.apply_damage(source, 4, opp)

# --- LIFE LOSS ---
class AliFromCairo(Listener):
    """Damage that would reduce your life total to less than 1 reduces it to 1 instead"""
    listens_to = LifeLossEvent

    def on_event(self, gs: GameState, s: GameCard, event: LifeLossEvent):
        if event.p_id_taking_damage != s.owner_id:
            return

        current_life = gs.score_mgr.life[event.p_id_taking_damage]

        if current_life - event.amt < 1:
            event.amt = max(current_life - 1, 0)

# --- MAIN PHASE ---
class ManaDrainMainPhase(Listener):
    """... At your next main phase, add an amount of {C} equal to that spell's mana value"""
    # TODO: Create ManaDrain(Resolver), which would create & register an instance of this class
    listens_to = MainPhaseEvent

    def __init__(self, mana_value: int):
        self.mana_value = mana_value

    def on_event(self, gs: GameState, source: GameCard, event: MainPhaseEvent) -> None:
        if event.active_p_id != source.owner_id:
            return
        gs.mana_pools[source.owner_id].add_floating('C', self.mana_value)
        gs.event_mgr.unregister_specific_effect(self)
