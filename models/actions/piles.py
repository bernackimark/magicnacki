from __future__ import annotations
import random
from typing import TYPE_CHECKING

from models.actions.base import Action
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

# --- GENERICS ---
class BattlefieldToGraveyard(Action):
    def __init__(self, p_id, gs, target: GameCard):
        super().__init__(p_id, gs)
        self.target = target

    def __repr__(self):
        return f'Move {self.target} to graveyard'

    def play(self) -> None:
        self.gs.pile_mgr.move_card(self.target, Zone.GRAVEYARD, cause='legendary_rule')
        self.finish()

class HandToBattlefield(Action):
    def __init__(self, p_id, gs, target: GameCard):
        super().__init__(p_id, gs)
        self.target = target

    def __repr__(self):
        return f'Move {self.target.props.name} from hand to battlefiend'

    def play(self):
        self.gs.pile_mgr.move_card(self.target, Zone.BATTLEFIELD, cause='hand_to_battlefield')
        self.finish()

class ReorderTopOfLibrary(Action):
    def __init__(self, p_id, gs, library_id: int, cards_in_order: list[GameCard]):
        super().__init__(p_id, gs)
        self.library_id = library_id
        self.cards_in_order = cards_in_order

    def __repr__(self):
        return f'Order top of library: {" ".join([c.props.name for c in self.cards_in_order])}'

    def play(self) -> None:
        """Delete the top x cards; iterate over cards_in_order back to front, placing each at position 0"""
        lib = self.gs.pile_mgr.libraries[self.library_id]
        del lib[:len(self.cards_in_order)]
        for c in self.cards_in_order[::-1]:
            lib.insert(0, c)
        self.finish()

class Shuffle(Action):
    def __init__(self, p_id, gs, cards: list[GameCard]):
        super().__init__(p_id, gs)
        self.cards = cards

    def __repr__(self):
        return 'Shuffle Cards'

    def play(self) -> None:
        random.shuffle(self.cards)
        self.finish()

class Tutor(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, tutored_card: GameCard, destination: Zone):
        super().__init__(p_id, gs)
        self.source = source
        self.tutored_card = tutored_card
        self.destination = destination

    def __repr__(self):
        return f'Tutor {self.tutored_card.props.name}'

    def play(self):
        self.gs.pile_mgr.move_card(self.tutored_card, self.destination)
        random.shuffle(self.gs.pile_mgr.libraries[self.player_idx])
        self.finish()

class TutorMultipleCards(Action):
    def __init__(self, p_id: int, gs: GameState, tutored_cards: list[GameCard], destination: Zone):
        super().__init__(p_id, gs)
        self.tutored_cards = tutored_cards
        self.destination = destination

    def __repr__(self):
        return (f'Move {", ".join([c.props.name for c in self.tutored_cards])} '
                f'from your library to your {self.destination.name}')

    def play(self):
        print('Library Count Before:', len(self.gs.pile_mgr.libraries[self.player_idx]))
        for c in self.tutored_cards:
            self.gs.pile_mgr.move_card(c, self.destination)
        random.shuffle(self.gs.pile_mgr.libraries[self.player_idx])
        print('Library Count After:', len(self.gs.pile_mgr.libraries[self.player_idx]))
        self.finish()
