from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base import Listener
from models.events_all import CostQueryEvent

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class Gloom(Listener):
    """White spells cost {3} more to cast. Activated abilities of white enchantments cost {3} more to activate."""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.systems.mana import ManaCost
        if (not (event.query == 'cast' and 'W' in event.card.colors) and not
           ('W' in event.card.colors and 'Enchantment' in event.card.card_types)):
            return
        event.cost = ManaCost(event.cost) + ManaCost('3')


class ManaMatrix(Listener):
    """Instant and enchantment spells you cast cost {2} less to cast"""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.systems.mana import ManaCost
        if event.query != 'cast' or event.player_id != s.owner_id:
            return
        if 'Instant' not in event.card.card_types and 'Enchantment' not in event.card.card_types:
            return
        event.cost = ManaCost(event.cost) - ManaCost('3')


class PlanarGate(Listener):
    """Creature spells you cast cost {2} less to cast"""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.systems.mana import ManaCost
        if event.query != 'cast' or event.player_id != s.owner_id or not event.card.is_creature:
            return
        event.cost = ManaCost(event.cost) - ManaCost('2')


class PowerArtifact(Listener):
    """Enchant artifact Enchanted artifact's activated abilities cost {2} less to activate.
    This effect can't reduce the mana in that cost to less than one mana."""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.systems.mana import ManaCost
        if event.query != 'activate' or event.card.host is not s:
            return
        event.cost = ManaCost(event.cost) - ManaCost('2')  # TODO: minimum '1' or a colored equivalent


class StoneCalendar(Listener):
    """Spells you cast cost {1} less to cast"""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.systems.mana import ManaCost
        if event.query != 'cast' or event.player_id != s.owner_id:
            return
        event.cost = ManaCost(event.cost) - ManaCost('1')
