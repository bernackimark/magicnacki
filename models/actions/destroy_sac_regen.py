from __future__ import annotations
from typing import TYPE_CHECKING

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

class DestroyAction(Action):
    def __init__(self, p_id, gs, source: GameCard, target: GameCard, allow_regen: bool = True):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target
        self.allow_regen = allow_regen

    def __repr__(self):
        return f'Destroy {self.target.props.name}'

    def play(self):
        self.gs.destroy(self.target, allow_regeneration=self.allow_regen)
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        if self.gs.pending_choice:
            self.gs.pending_choice = None

class Exile(Action):
    def __init__(self, p_id, gs, source: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.source = source
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Exile {self.source.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.source, self.w_damage_amt, self.source.owner_id)
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
        self.gs.destroy(self.source, False)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        elif len(self.gs.action_stack):
            self.gs.action_stack.pop()  # remove choice

class SacCards(Action):
    def __init__(self, p_id, gs, source: GameCard, cards: list[GameCard]):
        super().__init__(p_id, gs)
        self.source = source
        self.cards = cards

    def __repr__(self):
        return f'Sacrifice {", ".join([c.props.name for c in self.cards])}'

    def play(self):
        for c in self.cards:
            self.gs.destroy(c, False)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        elif len(self.gs.action_stack):
            self.gs.action_stack.pop()  # remove choice

# --- Card Specific ---
class TheAbyssAction(Action):
    def __init__(self, p_id, gs, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return f"{self.source.props.name}: Choose creature to destroy"

    def play(self):
        from models.choice_actions_all import TheAbyssChoice
        self.gs.pending_choice = TheAbyssChoice(self.player_idx, self.gs, self.source)
