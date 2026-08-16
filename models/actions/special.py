from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from models.action_stack import StackItemType
from models.actions.base import Action
from models.constants import KW, Zone
from models.game_card.counter_tokens import CounterType, WIND, PLUS_ONE
from models.effects.listeners_mod_queries import OwnershipModQuery
from models.events_all import StateBasedEvent
from models.game_card.modifiers import SubTypeMod
from models.systems.phase import Phase
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


# --- CARD-SPECIFIC ---
class CleansingDeclineAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "CleansingState"):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state

    def __repr__(self):
        return f"Decline saving Player #{self.state.active_land.owner_id}'s {self.state.active_land}"

    def play(self):
        from models.effects.resolvers_a_to_e import Cleansing
        self.state.player_cnt_acted_on_this_land += 1
        # Ask the next player
        self.gs.action_on_idx = flip(self.gs.action_on_idx)
        Cleansing.queue_next_choice(self.gs, self.s, self.state)

class CleansingPayAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "CleansingState"):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state

    def __repr__(self):
        return f"Pay 1 life to save Player #{self.state.active_land.owner_id}'s {self.state.active_land}"

    def play(self):
        from models.effects.resolvers_a_to_e import Cleansing
        self.gs.score_mgr.decrement_life(self.player_idx, 1, self.s, self.gs)
        self.state.saved_lands.append(self.state.active_land)

        # Move immediately to next land
        self.state.land_idx += 1
        self.gs.action_on_idx = flip(self.gs.action_on_idx)
        Cleansing.queue_next_choice(self.gs, self.s, self.state)

class DrafnaFinishAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "DrafnasRestoration.DrafnasRestorationState"):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state

    def __repr__(self):
        return "Finish selecting artifacts"

    def play(self) -> None:
        for card in self.state.selected_cards:
            self.gs.pile_mgr.move_card(card, Zone.LIBRARY)
        self.finish()

class DrafnaSelectCardAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "DrafnasRestoration.DrafnasRestorationState",
                 card: GameCard):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state
        self.card = card

    def __repr__(self):
        return f"Move {self.card.props.name} to library; subsequent artifacts will be placed above this card"

    def play(self) -> None:
        self.state.selected_cards.append(self.card)

class EurekaPlayCardAction(Action):
    def __init__(self, p_id: int, gs: GameState, state: "Eureka.EurekaState", card: GameCard):
        super().__init__(p_id, gs)
        self.state = state
        self.card = card

    def __repr__(self):
        return f"Play {self.card.props.name} to your board"

    def play(self) -> None:
        from models.effects.resolvers_a_to_e import Eureka
        self.gs.pile_mgr.move_card(self.card, Zone.BATTLEFIELD, cause='eureka', emit_zone_event=False)
        self.state.current_player = flip(self.player_idx)
        self.gs.pending_choice = None
        Eureka.queue_next_choice(self.gs, self.state)

class EurekaPlayerFinishAction(Action):
    def __init__(self, p_id: int, gs: GameState, state: "Eureka.EurekaState"):
        super().__init__(p_id, gs)
        self.state = state

    def __repr__(self):
        return f"Finish playing permanents to your board"

    def play(self) -> None:
        from models.effects.resolvers_a_to_e import Eureka
        self.state.players_who_are_done.append(self.player_idx)
        self.state.current_player = flip(self.player_idx)
        self.gs.pending_choice = None
        Eureka.queue_next_choice(self.gs, self.state)
