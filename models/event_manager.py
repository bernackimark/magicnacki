from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.effects.base import Effect, Listener
    from models.events_all import Event
    from models.game_card.game_card import GameCard
    from game_state import GameState


@dataclass
class ListenerEntry:
    effect: Listener
    source: GameCard

class EventManager:
    """Handles all effects who method is 'on_event'"""
    def __init__(self):
        # key = Event subclass, value = list of (effect, source_card) tuples
        self._event_listeners: dict[type[Event], list[ListenerEntry]] = defaultdict(list)

    def emit(self, event: Event, gs: GameState):
        """Call all effects listening to a certain type of event (ex: EndStepEvent)"""
        entries = list(self._event_listeners[type[event]])
        for e in entries:
            e.effect.on_event(gs, e.source, event)
        self.cleanup_expired()

    def register_effect(self, effect: Listener, source_card: GameCard):
        """Store the effect + source card tuple for later event emission."""
        if not isinstance(effect, Listener):
            raise TypeError(f"You are registering {effect} with EventManager that only accepts Listener Effects")
        listener_entry = ListenerEntry(effect, source_card)
        self._event_listeners[effect.listens_to].append(listener_entry)

    def unregister_effects(self, card: GameCard):
        """Remove any event listeners tied to this card"""
        for event_type, entries in self._event_listeners.items():
            # Keep only effects whose source_card is not the leaving card
            self._event_listeners[event_type] = [entry for entry in entries if entry.source != card]

    def unregister_specific_effect(self, effect: Effect):
        """Used when an effect is neither unregistered when the source leaves the battlefield nor at EOT
        (ex: Abomination destroying a creature that blocked it at the end of combat)"""
        for event_type, entries in self._event_listeners.items():
            self._event_listeners[event_type] = [entry for entry in entries if entry.effect != effect]

    def cleanup_eot(self):
        for event_type, entries in self._event_listeners.items():
            self._event_listeners[event_type] = [e for e in entries if e.effect.expires != 'EOT']

    def cleanup_expired(self):
        for event_type, entries in self._event_listeners.items():
            self._event_listeners[event_type] = [e for e in entries if not e.effect.is_expired]
