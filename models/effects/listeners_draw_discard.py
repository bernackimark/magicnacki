from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.constants import Zone
from models.game_card.counter_tokens import DOOM
from models.effects.base import Listener
from models.events_all import DiscardEvent, DiscardStepEvent, DrawCardEvent, DrawStepEvent
from models.systems.phase import Phase
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


# --- DISCARD EVENT ---
class PsychicPurgeDiscard(Listener):
    """... When a spell or ability an opponent controls causes you to discard this card, that player loses 5 life"""
    listens_to = DiscardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        if not event.source or event.source.owner_id != source.owner_id:
            return
        gs.apply_damage(source, 5, event.source.owner_id)


# --- DISCARD STEP EVENT ---
class CursedRack(Listener):
    """Opponent's maximum hand size is four [at their discard phase]"""
    listens_to = DiscardStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardStepEvent):
        opp_id = flip(source.owner_id)
        if event.active_player != opp_id:
            return

        hand = gs.pile_mgr.hands[opp_id]
        overage = len(hand) - 4
        combos: list[list[GameCard]] = [_ for _ in combinations(hand, r=overage)]
        options = [CO(f"Discard {', '.join([c.props.name for c in combo])}",
                      lambda: gs.pile_mgr.discards(combo)) for combo in combos]
        gs.queue_choice(ChoiceAction(options))


# --- DRAW EVENT ---
class FastingDestroy(Listener):
    """When you draw a card, destroy this enchantment"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if event.player_id == source.owner_id:
            gs.pile_mgr.destroy(source)

class UnderworldDreams(Listener):
    """Whenever an opponent draws a card, this enchantment deals 1 damage to that player"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if source.owner_id == event.player_id:
            return
        gs.apply_damage(source, 1, event.player_id)


# --- DRAW STEP EVENT ---
class ArmageddonClockDrawStep(Listener):
    """... At your draw step, AC deals damage = its doom counters to each player ... """
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        if ctr_cnt := source.counters.get_count(DOOM):
            gs.apply_damage(source, ctr_cnt, source.owner_id)
            gs.apply_damage(source, ctr_cnt, flip(source.owner_id))

class HowlingMine(Listener):
    """At each player's draw step, if this artifact is untapped, that player draws an additional card"""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent):
        if source.is_tapped:
            return
        gs.pile_mgr.draw(event.active_player)

class IslandSanctuary(Listener):
    """At your draw step, you may skip your draw and until your next turn,
    you can only be attacked by creatures with flying and/or islandwalk"""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        option_text = 'Skip your draw & until your next turn, you can only be attacked by fliers and/or islandwalkers'
        options = [CO(option_text, lambda: self.island_sanctuary_method(gs, source))]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def island_sanctuary_method(gs: GameState, s: GameCard):
        from models.effects.listeners_permission import IslandSanctuaryRestriction
        from models.effects.listeners_generic import UnregisterListenerOnYourNextTurn
        gs.phase_mgr.set_phase(Phase.MAIN)
        listener = IslandSanctuaryRestriction()
        gs.event_mgr.register(listener, s)
        gs.event_mgr.register(UnregisterListenerOnYourNextTurn(listener), s)

class ManaVaultDamageIfTapped(Listener):
    """... At your draw step, if this artifact is tapped, it deals 1 damage to you ..."""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: DrawStepEvent):
        if event.active_player != s.owner_id or not s.is_tapped:
            return
        gs.apply_damage(s, 1, s.owner_id)

class SylvanLibrary(Listener):
    """At your draw step, you may draw two additional cards ..."""
    listens_to = DrawStepEvent

    @dataclass
    class SylvanLibraryState:
        drawn_cards: list[GameCard]
        selected_cards: list[GameCard] = field(default_factory=list)

    def on_event(self, gs: GameState, s: GameCard, event: DrawStepEvent) -> None:
        if event.active_player != s.owner_id:
            return

        options = [CO(f'Draw two additional cards with {s}', lambda: self.draw_two(s.owner_id, gs, s))]
        gs.queue_choice(ChoiceAction(options, may=True))

    def queue_card_decision(self, gs: GameState, s: GameCard, state: SylvanLibraryState, card: GameCard) -> None:
        options = [CO(f'Pay 4 life for {card}', lambda: self.pay_life(s.owner_id, gs, s, state)),
                   CO(f'Put {card} atop your library', lambda: self.put_on_top(gs, s, state, card))]
        gs.queue_choice(ChoiceAction(options))

    def queue_next_card_selection(self, gs: GameState, source: GameCard, state: SylvanLibraryState) -> None:
        if len(state.selected_cards) >= 3:
            return
        remaining = [card for card in state.drawn_cards if card not in state.selected_cards]
        options = [CO(self.select_card_text(state, c), lambda: self.select_card(gs, source, state, c))
                   for c in remaining]
        gs.queue_choice(ChoiceAction(options))

    def draw_two(self, p_id: int, gs: GameState, s: GameCard):
        gs.pile_mgr.draw(p_id, 2)
        cards_drawn = [e.card for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)
                       if e.player_id == p_id]
        state = self.SylvanLibraryState(drawn_cards=cards_drawn[:])
        gs.choice_mgr.clear_current()
        self.queue_next_card_selection(gs, s, state)

    def pay_life(self, p_id: int, gs: GameState, s: GameCard, state: SylvanLibraryState):
        gs.score_mgr.decrement_life(p_id, 4, s, gs)
        gs.choice_mgr.clear_current()
        self.queue_next_card_selection(gs, s, state)

    def put_on_top(self, gs: GameState, s: GameCard, state: SylvanLibraryState, card: GameCard):
        gs.pile_mgr.move_card(card, Zone.LIBRARY, cause='sylvan-library')
        gs.choice_mgr.clear_current()
        self.queue_next_card_selection(gs, s, state)

    def select_card(self, gs: GameState, s: GameCard, state: SylvanLibraryState, card: GameCard):
        state.selected_cards.append(card)
        gs.choice_mgr.clear_current()
        if len(state.selected_cards) == 1:
            self.queue_next_card_selection(gs, s, state)
        else:
            self.queue_card_decision(gs, s, state, card)

    @staticmethod
    def select_card_text(state: SylvanLibraryState, card: GameCard):
        if not state.selected_cards:
            return f'Select {card} as your free draw card'
        return f'Select {card} to either add to your hand for 4 life or place atop your library'
