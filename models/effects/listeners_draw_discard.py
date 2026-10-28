from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
import random
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.constants import Zone
from models.game_card.counter_tokens import DOOM
from models.effects.base import Listener
from models.events_all import DiscardEvent, DiscardStepEvent, DrawCardEvent, DrawStepEvent, DrawCardAllowedQueryEvent, \
    Event
from models.presentation_request import PresentationReqType
from models.systems.emblem import Emblem
from models.systems.phase import Phase
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


# --- DISCARD EVENT ---
class LibraryOfLengDiscard(Listener):
    """If an effect causes you to discard a card, discard it,
    but you may put it on top of your library instead of into your graveyard."""
    listens_to = DiscardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent) -> None:
        if event.active_player != source.owner_id:
            return
        options = [CO(f'Move {event.card} to the top of your library instead of your graveyard',
                   lambda: gs.pile_mgr.move_card(event.card, Zone.LIBRARY))]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

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
        gs.choice_mgr.queue(ChoiceAction(options))


# --- DRAW CARD PROPOSED EVENT ---
class AladdinsLampListener(Listener):
    """The next time you would draw a card this turn, instead look at the top X (X > 0) cards of your library,
    put all but one of them on the bottom of your library in a random order, then draw a card."""
    listens_to = DrawCardAllowedQueryEvent

    def __init__(self, x_value: int):
        self.x_value = x_value

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardAllowedQueryEvent) -> None:
        if event.player_id != source.owner_id:
            return
        lib = gs.pile_mgr.libraries[source.owner_id]
        x = min(len(lib), self.x_value)
        top_x_cards = lib[:x]
        gs.add_presentation_request(source.owner_id, PresentationReqType.VIEW_LIBRARY, {'cards': top_x_cards})
        options = [CO(f'Place {c} atop your library',
                      lambda card=c: self._select_card(card, lib, top_x_cards)) for c in top_x_cards]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def _select_card(selected_card: GameCard, lib: list[GameCard], top_x_cards: list[GameCard]):
        unselected_cards = [c for c in top_x_cards if c is not selected_card]
        [lib.remove(c) for c in unselected_cards]
        random.shuffle(unselected_cards)
        [lib.append(c) for c in unselected_cards]

class ChainsOfMephistopheles(Listener):
    """If a player would draw a 2nd card in a turn ... If no cards in hand, mill; else, discard then draw."""
    listens_to = DrawCardAllowedQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardAllowedQueryEvent) -> None:
        p_id = event.player_id
        hand = gs.hands[p_id]
        drawn_cnt = len([e for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)
                         if e.player_id == p_id])
        if not drawn_cnt:
            return

        event.permission = False
        if not hand:
            gs.pile_mgr.mill(p_id)
            return
        options = [CO(f'Discard {c}', lambda card=c: self._discard_then_draw(gs, p_id, card)) for c in hand]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def _discard_then_draw(gs: GameState, p_id: int, selected_discard: GameCard):
        gs.pile_mgr.discard(selected_discard)
        top_lib_card = gs.pile_mgr.libraries[p_id][0]
        gs.pile_mgr.move_card(top_lib_card, Zone.HAND, cause='chains-of-mephistopheles')

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

class IslandSanctuary(Listener):
    """At your draw step, you may skip your draw and until your next turn,
    you can only be attacked by creatures with flying and/or islandwalk"""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        option_text = 'Skip your draw & until your next turn, you can only be attacked by fliers and/or islandwalkers'
        options = [CO(option_text, lambda: self.island_sanctuary_method(gs, source))]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    @staticmethod
    def island_sanctuary_method(gs: GameState, s: GameCard):
        from models.effects.listeners_permission import IslandSanctuaryRestriction
        from models.effects.listeners_generic import UnregisterListenerOnYourNextTurn
        gs.phase_mgr.set_phase(Phase.MAIN)
        listener = IslandSanctuaryRestriction()
        gs.event_mgr.register(listener, s)
        gs.event_mgr.register(UnregisterListenerOnYourNextTurn(listener), s)

class NafsAspUnpaid(Listener):
    """Whenever NA deals damage to opp, at any point up to their next draw phase, opp pays {1} or loses 1 life.
    This Listener triggers at the opponent's draw phase, deals 1 damage, and removes the emblem"""
    listens_to = DrawStepEvent

    def __init__(self, paying_player: int):
        self.paying_player = paying_player

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent) -> None:
        if event.active_player != self.paying_player:
            return

        # Source of the damage cannot be Nafs Asp because it will create an infinte loop of creating this Listener
        gs.apply_damage(None, 1, self.paying_player)
        for em in gs.emblem_mgr.emblems:
            if em.source is source:
                gs.emblem_mgr.remove_emblem(em)
                gs.event_mgr.unregister_specific_effect(self)
                return

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
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    def queue_card_decision(self, gs: GameState, s: GameCard, state: SylvanLibraryState, card: GameCard) -> None:
        options = [CO(f'Pay 4 life for {card}', lambda: self.pay_life(s.owner_id, gs, s, state)),
                   CO(f'Put {card} atop your library', lambda: self.put_on_top(gs, s, state, card))]
        gs.choice_mgr.queue(ChoiceAction(options))

    def queue_next_card_selection(self, gs: GameState, source: GameCard, state: SylvanLibraryState) -> None:
        if len(state.selected_cards) >= 3:
            return
        remaining = [card for card in state.drawn_cards if card not in state.selected_cards]
        options = [CO(self.select_card_text(state, c), lambda: self.select_card(gs, source, state, c))
                   for c in remaining]
        gs.choice_mgr.queue(ChoiceAction(options))

    def draw_two(self, p_id: int, gs: GameState, s: GameCard):
        gs.pile_mgr.draw(p_id, 2)
        cards_drawn = [e.card for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)
                       if e.player_id == p_id]
        state = self.SylvanLibraryState(drawn_cards=cards_drawn[:])
        gs.choice_mgr.clear_current()
        self.queue_next_card_selection(gs, s, state)

    def pay_life(self, p_id: int, gs: GameState, s: GameCard, state: SylvanLibraryState):
        gs.score_mgr.decrement_life(p_id, 4, s)
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
