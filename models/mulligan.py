from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.constants import Mulligan
from models.phase_manager import Phase

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.choice_actions_all import ChoiceAction

"""
Flow:
    -   User is presented with MulliganChoice; available actions are dictated by rule
        -   Original: can only mulligan if no lands or all lands, and you've not already mulliganed
        -   London: for each mulligan taken (<= 7), when you keep your hand, you must move one card to bottom of library
        -   Paris: for each mulligan taken (<= 7), draw one fewer card
        -   ... w Gentlemen's: the mulligan doesn't count, it's as if you never drew those cards
    -   If there are no possible actions, clear GameState.pending_choice & return no Action
    -   Present user with a list of Action (Take Mulligan, Take Gentlemen's Mulligan, Keep Hand)
    -   KeepHand.play() exits flow
    -   If using London rule, enter BottomChoice flow:
        -   Select a card to be bottomed, add to BottomChoice selected until count of cards is met
        -   Once met, present only FinishBottom
    -   FinishBottom.play() exits flow
    -   When exiting flow, set GameState.phase == Phase.CAST, as On The Play player does not get to draw
"""

class MulliganChoice(ChoiceAction):
    def __init__(self, p_id, gs, rule: Mulligan):
        super().__init__(p_id, gs, source=None)
        self.rule = rule
        self.mulligans_taken = 0

    def get_card_cnt_to_be_drawn(self) -> int:
        if self.rule in (Mulligan.PARIS, Mulligan.PARIS_WITH_GENTLEMENS):
            return 7 - self.mulligans_taken
        else:
            return 7

    def is_all_or_no_lands(self) -> bool:
        hand = self.gs.hands[self.player_idx].cards
        lands = [c for c in hand if c.props.is_land]
        return len(lands) in (0, len(hand))

    def get_actions(self) -> list[Action]:
        if self.rule == Mulligan.ORIGINAL:
            if self.is_all_or_no_lands() and not self.mulligans_taken:
                return [TakeMulligan(self.player_idx, self.gs, self), KeepHand(self.player_idx, self.gs, self)]
            self.gs.pending_choice = None
            return []  # is this enough to get out of this flow?
        if self.is_all_or_no_lands():
            return [TakeGentlemensMulligan(self.player_idx, self.gs, self), KeepHand(self.player_idx, self.gs, self)]
        if self.mulligans_taken >= 7:
            self.gs.pending_choice = None
            return []
        return [TakeMulligan(self.player_idx, self.gs, self), KeepHand(self.player_idx, self.gs, self)]


class BottomChoice(ChoiceAction):
    def __init__(self, p_id, gs, bottom_cnt: int):
        super().__init__(p_id, gs, source=None)
        self.bottom_cnt = bottom_cnt
        self.selected: list[GameCard] = []

    def get_actions(self) -> list[Action]:
        if len(self.selected) == self.bottom_cnt:
            return [FinishBottoming(self.player_idx, self.gs, self)]

        hand_cards = self.gs.hands[self.player_idx].cards
        return [BottomFromHand(self.player_idx, self.gs, self, c) for c in hand_cards if c not in self.selected]

@dataclass
class BottomFromHand(Action):
    choice: BottomChoice
    card: GameCard

    def __repr__(self):
        return f"Bottom {self.card.props.name}"

    def play(self) -> None:
        self.choice.selected.append(self.card)

@dataclass
class TakeMulligan(Action):
    choice: MulliganChoice

    def __repr__(self):
        return 'Take Mulligan'

    def play(self):
        self.choice.mulligans_taken += 1
        self.gs.libraries[self.player_idx].extend(self.gs.hands[self.player_idx].cards)
        self.gs.hands[self.player_idx].cards.clear()
        self.gs.draw(self.player_idx, self.choice.get_card_cnt_to_be_drawn())
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

@dataclass
class TakeGentlemensMulligan(Action):
    choice: MulliganChoice

    def __repr__(self):
        return "Take Gentlemen's Mulligan"

    def play(self):
        self.gs.libraries[self.player_idx].extend(self.gs.hands[self.player_idx].cards)
        self.gs.hands[self.player_idx].cards.clear()
        self.gs.draw(self.player_idx, self.choice.get_card_cnt_to_be_drawn())
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

@dataclass
class KeepHand(Action):
    choice: MulliganChoice

    def __repr__(self):
        return 'Keep Hand'

    def play(self):
        if self.choice.rule in (Mulligan.LONDON, Mulligan.LONDON_WITH_GENTLEMENS) and self.choice.mulligans_taken > 0:
            self.gs.pending_choice = BottomChoice(self.player_idx, self.gs, self.choice.mulligans_taken)
            return
        self.gs.pending_choice = None
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        self.gs.phase_mgr.set_phase(Phase.MAIN, self.gs)

@dataclass
class FinishBottoming(Action):
    choice: BottomChoice

    def __repr__(self):
        return "Finish Mulligan"

    def play(self):
        for card in self.choice.selected:
            self.gs.hands[self.player_idx].cards.remove(card)
            self.gs.libraries[self.player_idx].append(card)
        self.gs.pending_choice = None
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        self.gs.phase_mgr.set_phase(Phase.MAIN, self.gs)
