from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING

from models.actions.draw_discard import DiscardCards, SylvanLibraryDraw
from models.actions.special import IslandSanctuaryAction
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import DOOM
from models.effects.base import Listener
from models.events_all import DiscardEvent, DiscardStepEvent, DrawCardEvent, DrawStepEvent, Event
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
        combos = [_ for _ in combinations(hand, r=overage)]
        options = [DiscardCards(opp_id, gs, combo) for combo in combos]
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
        options = [IslandSanctuaryAction(source.owner_id, gs, source)]
        gs.queue_choice(ChoiceAction(options, may=True))

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
        source: GameCard
        top_3_cards: list[GameCard]
        selected_drawn: list[GameCard] = field(default_factory=list)
        selected_ordered: list[GameCard] = field(default_factory=list)
        status = 'drawing'

        @property
        def life_owed_to_draw(self) -> int:
            return 4 if len(self.selected_drawn) else 0

        @property
        def is_done(self) -> bool:
            return len(self.selected_drawn) + len(self.selected_ordered) >= 3

        @property
        def unaddressed_cards(self) -> list[GameCard]:
            return [c for c in self.top_3_cards if c not in self.selected_drawn and c not in self.selected_ordered]

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        lib = gs.pile_mgr.libraries[source.owner_id]
        if len(lib) < 3:
            return
        top_3_cards = gs.pile_mgr.libraries[source.owner_id][:3]
        options = [SylvanLibraryDraw(source.owner_id, gs, SylvanLibrary.SylvanLibraryState(source, top_3_cards))]
        gs.pending_choice = ChoiceAction(options, may=True)
