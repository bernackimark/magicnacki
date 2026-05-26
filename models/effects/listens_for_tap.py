from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import MINUS_ZERO_TWO
from models.effects.base import Effect
from models.events_all import TapCardEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class Blight(Effect):
    """Enchant land; When enchanted land becomes tapped, destroy it."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if not source.host or source.props.slug != 'blight' or event.card is not source.host:
            return
        gs.destroy(source.host)


class WildGrowth(Effect):
    """Enchant land Whenever enchanted land is tapped for mana, its controller adds another {G}"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if source.host is not event.card:
            return
        gs.mana_pools[event.card.owner_id].add_floating('G')


class SpiritShackle(Effect):
    """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.host:
            return
        s.host.counters.add_counter(MINUS_ZERO_TWO)


class CityOfBrassDamageOnTap(Effect):
    """Whenever this land becomes tapped, it deals 1 damage to you"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if event.card is not source:
            return
        gs.apply_damage(source, 1, source.owner_id)


class Lifeblood(Effect):
    """Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card.owner_id == s.owner_id:
            return
        if 'Mountain' in event.card.card_sub_types:
            gs.score_mgr.increment_life(s.owner_id, 1, s, gs)


class Lifetap(Effect):
    """Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card.owner_id == s.owner_id:
            return
        if 'Forest' in event.card.card_sub_types:
            gs.score_mgr.increment_life(s.owner_id, 1, s, gs)


class PsychicVenom(Effect):
    """Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.host:
            return
        gs.apply_damage(s, 2, event.card.owner_id)
