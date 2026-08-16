from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.events_all import DrawCardEvent
from models.constants import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.base import Action


# --- CARD SPECIFIC ---
@dataclass
class SylvanLibraryPayLifeAction(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard,
                 state: "SylvanLibrary.SylvanLibraryState", card: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.state = state
        self.card = card

    def __repr__(self):
        return f'Pay 4 life for {self.card.props.name}'

    def play(self) -> None:
        from models.effects.listeners_draw_discard import SylvanLibrary
        self.gs.score_mgr.decrement_life(self.player_idx, 4, self.source, self.gs)
        self.gs.pending_choice = None
        SylvanLibrary.queue_next_card_selection(self.gs, self.source, self.state)

@dataclass
class SylvanLibraryPutOnTopAction(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard,
                 state: "SylvanLibrary.SylvanLibraryState", card: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.state = state
        self.card = card

    def __repr__(self):
        return f'Put {self.card.props.name} on top of your library'

    def play(self) -> None:
        from models.effects.listeners_draw_discard import SylvanLibrary
        self.gs.pile_mgr.move_card(self.card, Zone.LIBRARY, cause='sylvan-library')
        self.gs.pending_choice = None
        SylvanLibrary.queue_next_card_selection(self.gs, self.source, self.state)

@dataclass
class SylvanLibrarySelectCardAction(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard,
                 state: "SylvanLibrary.SylvanLibraryState", card: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.state = state
        self.card = card

    def __repr__(self):
        if not self.state.selected_cards:
            return f'Select {self.card.props.name} as your free draw card'
        return f'Select {self.card.props.name} to either add to your hand for 4 life or place atop your library'

    def play(self) -> None:
        from models.effects.listeners_draw_discard import SylvanLibrary
        self.state.selected_cards.append(self.card)
        self.gs.pending_choice = None

        if len(self.state.selected_cards) == 1:
            SylvanLibrary.queue_next_card_selection(self.gs, self.source, self.state)
            return

        SylvanLibrary.queue_card_decision(self.gs, self.source, self.state, self.card)

@dataclass
class SylvanLibraryDrawTwoAction(Action):

    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return 'Draw two additional cards with Sylvan Library'

    def play(self) -> None:
        from models.effects.listeners_draw_discard import SylvanLibrary
        self.gs.pile_mgr.draw(self.player_idx, 2)
        cards_drawn = [e.card for e in self.gs.event_mgr.get_events(self.gs.turn_mgr.turn_number, DrawCardEvent)
                       if e.player_id == self.player_idx]
        state = SylvanLibrary.SylvanLibraryState(drawn_cards=cards_drawn[:])
        self.gs.pending_choice = None
        SylvanLibrary.queue_next_card_selection(self.gs, self.source, state)
