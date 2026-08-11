from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.base import Action
from models.systems.phase import Phase


@dataclass
class DrawCard(Action):
    def __repr__(self) -> str:
        return 'Draw a Card'

    def play(self) -> None:
        self.gs.pile_mgr.draw(self.player_idx)
        self.finish()

@dataclass
class DiscardCards(Action):
    cards: GameCard | list[GameCard]

    def __repr__(self) -> str:
        if not isinstance(self.cards, list):
            return f"Discard {self.cards} to graveyard"
        else:
            return f"Discard {', '.join([c.__repr__() for c in self.cards])} to graveyard"

    def play(self) -> None:
        if not isinstance(self.cards, list):
            self.cards = [self.cards]
        for c in self.cards[::]:
            print(f"Discarding {c} from player {self.player_idx}'s hand")
            self.gs.pile_mgr.discard(c)
        self.finish()

@dataclass
class MoveToDrawPhase(Action):

    def __repr__(self) -> str:
        return "Move to Draw Phase"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        self.finish()


# --- CARD SPECIFIC ---
@dataclass
class SylvanMoveCardToHand(Action):
    def __init__(self, p_id: int, gs: GameState, card: GameCard, state: "SylvanLibraryListener.SylvanLibraryState"):
        super().__init__(p_id, gs)
        self.card = card
        self.state = state

    def __repr__(self):
        pay_life_text = f': Pay {self.state.life_owed_to_draw}' if self.state.life_owed_to_draw else ''
        return f"Draw {self.card}{pay_life_text}"

    def play(self) -> None:
        self.state.selected_drawn.append(self.card)
        if self.state.life_owed_to_draw:
            self.gs.score_mgr.decrement_life(self.player_idx, self.state.life_owed_to_draw, self.state.source, self.gs)
        if self.state.is_done:
            self.finish()
            return
        self.gs.pending_choice = None
        options = [SylvanMoveCardToHand(self.player_idx, self.gs, c, self.state) for c in self.state.unaddressed_cards] + \
                  [SylvanFinishDrawing(self.player_idx, self.gs, self.state)]
        self.gs.queue_choice(ChoiceAction(options))

@dataclass
class SylvanPlaceOnLibrary(Action):
    def __init__(self, p_id: int, gs: GameState, card: GameCard, state: "SylvanLibraryListener.SylvanLibraryState"):
        super().__init__(p_id, gs)
        self.card = card
        self.state = state

    def __repr__(self):
        return f"Move {self.card.props.name} to library; subsequent card will be placed above this card"

    def play(self) -> None:
        self.gs.pile_mgr.libraries[self.player_idx].insert(0, self.card)
        self.state.selected_ordered.append(self.card)
        if not self.state.unaddressed_cards:
            self.finish()
            return
        last_card = self.state.unaddressed_cards[0]
        self.gs.pile_mgr.libraries[self.player_idx].insert(0, last_card)
        self.state.remaining_cards.remove(last_card)
        self.finish()

@dataclass
class SylvanFinishDrawing(Action):
    def __init__(self, p_id: int, gs: GameState, state: "SylvanLibraryListener.SylvanLibraryState"):
        super().__init__(p_id, gs)
        self.state = state

    def __repr__(self):
        return 'Finish drawing'

    def play(self) -> None:
        self.state.status = 'ordering'
        self.gs.pending_choice = None
        options = [SylvanPlaceOnLibrary(self.player_idx, self.gs, c, self.state)
                   for c in self.state.unaddressed_cards]
        self.gs.queue_choice(ChoiceAction(options))

@dataclass
class SylvanLibraryDraw(Action):
    def __init__(self, p_id: int, gs: GameState, state: "SylvanLibraryListener.SylvanLibraryState"):
        super().__init__(p_id, gs)
        self.state = state

    def __repr__(self):
        return "Draw two extra cards"

    def play(self) -> None:
        self.gs.add_presentation_request(self.player_idx, 'view_library', {'cards': self.state.top_3_cards})
        self.gs.pending_choice = None
        options = [SylvanMoveCardToHand(self.player_idx, self.gs, c, self.state) for c in self.state.top_3_cards]
        self.gs.queue_choice(ChoiceAction(options))
