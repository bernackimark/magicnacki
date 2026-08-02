from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.events_all import Event
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.effects.base import Listener
from models.effects.base_listeners import BaseRule
from models.events_all import ModQueryEvent

@dataclass
class ListenerEntry:
    effect: Listener
    source: GameCard

    def __repr__(self):
        return f"{self.source.props.name}'s {self.effect.__repr__()}"

class EventManager:
    """Handles all Listener effects who method is 'on_event' -- both base rules & card-based effects"""
    def __init__(self, gs: GameState):
        self._gs = gs
        self._events: list[tuple[Event, int]] = []

        # key = Event subclass, value = list of (effect, source_card) tuples
        self._base_rule_listeners: dict[type[Event], list[Listener]] = defaultdict(list)
        self._event_listeners: dict[type[Event], list[ListenerEntry]] = defaultdict(list)
        self._register_base_listeners()

    @property
    def events(self) -> list[Event | None]:
        return [event for event, _ in self._events]

    @property
    def event_listeners(self) -> dict[type[Event], list[ListenerEntry]]:
        return self._event_listeners

    def get_events(self, turn_number: int | None = None, event: Event | None = None) -> list[Event | None]:
        if not turn_number and not event:
            return self.events
        if turn_number and not event:
            return [event for event, turn_num in self._events if turn_num == turn_number]
        if event and not turn_number:
            return [e for e in self.events if isinstance(e, event)]  # type: ignore
        return [e for e, turn_num in self._events if turn_num == turn_number and isinstance(e, event)]  # type: ignore

    def emit(self, event: Event):
        """Call all effects listening to a certain type of event (ex: EndStepEvent); log that Event in Event Mgr;
        if gs.choice_queue has items but there is no gs.pending_choice, pop from choice_queue to pending_choice"""
        self._events.append((event, self._gs.turn_mgr.turn_number))

        for base_rule in self._base_rule_listeners[type(event)]:
            source = event.source if hasattr(event, 'source') else None
            base_rule.on_event(self._gs, source, event)  # rare case where the 'source' argument is not supplied

        entries = list(self._event_listeners[type(event)])
        for e in entries:
            if isinstance(event, ModQueryEvent):
                # enforce type contract
                if hasattr(e.effect, "modifies"):
                    if e.effect.modifies != event.query:
                        continue
            print(f'Emitting {type(event).__name__}, possible responder {e}')
            e.effect.on_event(self._gs, e.source, event)

        if not self._gs.pending_choice and self._gs.choice_queue:
            self._gs.pending_choice = self._gs.choice_queue.pop(0)

        self.cleanup_expired()

    def register(self, effect: Listener, source_card: GameCard):
        """Store the effect + source card tuple for later event emission."""
        if not isinstance(effect, Listener):
            raise TypeError(f"You are registering {effect} with EventManager that only accepts Listener Effects")
        listener_entry = ListenerEntry(effect, source_card)
        self._event_listeners[effect.listens_to].append(listener_entry)

    def register_card(self, card: GameCard):
        """Registers all listeners for the card"""
        for eff_spec in card.abilities:
            if not isinstance(eff_spec.effect, Listener):
                continue
            self.register(eff_spec.effect, card)
            print(f"Registered listener for {card.props.name}: {eff_spec.effect}")

    def unregister_effects(self, card: GameCard):
        """Remove any event listeners tied to this card"""
        for event_type, entries in self._event_listeners.items():
            # Keep only effects whose source_card is not the leaving card
            self._event_listeners[event_type] = [entry for entry in entries if entry.source != card]

    def unregister_specific_effect(self, effect: Listener):
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

    def _register_base_listeners(self) -> None:
        for base_rule in BaseRule.registry:
            self._base_rule_listeners[base_rule.listens_to].append(base_rule())
