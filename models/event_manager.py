from __future__ import annotations
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.effects.base import Effect
    from models.events_all import Event
    from models.game_card.game_card import GameCard
    from game_state import GameState


class EventManager:
    """Handles all effects who method is 'on_event'"""
    def __init__(self):
        # key = Event subclass, value = list of (effect, source_card) tuples
        self._event_listeners: dict[type, list[tuple[Effect, GameCard]]] = defaultdict(list)

    def emit(self, event: Event, gs: GameState):
        """Call all effects listening to a certain type of event (ex: EndStepEvent); only Effects w 'on_event' listen"""
        for eff, source_card in self._event_listeners[type(event)]:
            if hasattr(eff, 'on_event'):
                eff.on_event(gs, source_card, event)

    def register_effect(self, effect: Effect, source_card: GameCard):
        """Store the effect + source card tuple for later event emission."""
        if effect and effect.listens_to:
            self._event_listeners[effect.listens_to].append((effect, source_card))

    def unregister_effects(self, card: GameCard):
        """Remove any event listeners tied to this card."""
        for event_type, effect_list in self._event_listeners.items():
            # Keep only effects whose source_card is not the leaving card
            self._event_listeners[event_type] = [(eff, source) for eff, source in effect_list if source != card]

    def unregister_specific_effect(self, effect: Effect):
        """Used when an effect is neither unregistered when the source leaves the battlefield nor at EOT
        (ex: Abomination destroying a creature that blocked it at the end of combat)"""
        for event_type, effect_list in self._event_listeners.items():
            self._event_listeners[event_type] = [(eff, source) for eff, source in effect_list if eff != effect]
