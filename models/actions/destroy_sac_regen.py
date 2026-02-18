from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

from models.utils import flip

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.actions.base import Action

class AllowOpponentToDestroyALand(Action):
    def __init__(self, p_id, gs, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return f'Allow Opponent to Destroy One of Your Lands'

    def play(self) -> None:
        if self.gs.action_stack:
            self.gs.action_stack.pop()
            # must first pop Demonic Hordes' controller's choice to pay
        from models.choice_actions_all import OpponentDestroysLandChoice
        self.gs.action_stack.push(OpponentDestroysLandChoice(flip(self.player_idx), self.gs, self.source), self.gs, True)

class Destroy(Action):
    def __init__(self, p_id, gs, source: GameCard, target: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target

    def __repr__(self):
        return f'Destroy {self.target.props.name}'

    def play(self):
        self.gs.destroy(self.target)
        self.gs.action_stack.pop()  # remove choice

class Exile(Action):
    def __init__(self, p_id, gs, source: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.source = source
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Exile {self.source.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.source, self.w_damage_amt, self.source.orig_owner_id)
        self.gs.exile(self.source)
        self.gs.action_stack.pop()  # remove choice

class Reanimate(Action):
    def __init__(self, p_id, gs, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return f'Reanimate {self.source.props.name}'

    def play(self):
        self.gs.reanimate(self.source)
        self.gs.action_stack.pop()  # remove choice

class Sac(Action):
    def __init__(self, p_id, gs, source: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.source = source
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Sacrifice {self.source.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.source, self.w_damage_amt, self.source.owner_id)
        self.gs.destroy(self.source)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        elif len(self.gs.action_stack):
            self.gs.action_stack.pop()  # remove choice
