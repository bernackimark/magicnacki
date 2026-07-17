from __future__ import annotations
from typing import TYPE_CHECKING

from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

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
        from models.choice_actions_all import ChoiceAction
        options = [DestroyAction(flip(self.player_idx), self.gs, self.source, land)
                   for land in self.gs.card_filter.lands().on_player_board(self.player_idx).result()]
        self.gs.pending_choice = ChoiceAction(options)

class DestroyAction(Action):
    def __init__(self, p_id, gs, source: GameCard, target: GameCard, allow_regen: bool = True):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target
        self.allow_regen = allow_regen

    def __repr__(self):
        return f'Destroy {self.target.props.name}'

    def play(self):
        self.gs.pile_mgr.destroy(self.target, allow_regeneration=self.allow_regen)
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
        self.gs.pile_mgr.exile(self.source)
        self.gs.action_stack.pop()  # remove choice

class ReanimateAction(Action):
    def __init__(self, p_id, gs, source: GameCard, target: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target

    def __repr__(self):
        return f'Reanimate {self.target.props.name}'

    def play(self):
        self.gs.pile_mgr.reanimate(self.target)

class SacToReturnAllCardsExiledBy(Action):
    def __init__(self, p_id, gs, source: GameCard, exiler: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.exiler = exiler

    def __repr__(self):
        return f'Sacrifice {self.exiler.props.name} to return all cards it exiled to the battlefield'

    def play(self) -> None:
        if self.exiler.extras.get('cards_exiled') is None:
            return
        for card in self.exiler.extras.get('cards_exiled'):
            self.gs.pile_mgr.reanimate(card)
        del self.exiler.extras['cards_exiled']
        self.gs.pile_mgr.destroy(self.exiler, allow_regeneration=False)

class Sac(Action):
    def __init__(self, p_id, gs, target: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.target = target
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Sacrifice {self.target.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.target, self.w_damage_amt, self.target.owner_id)
        self.gs.pile_mgr.destroy(self.target, False)
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
            self.gs.pile_mgr.destroy(c, False)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        elif len(self.gs.action_stack):
            self.gs.action_stack.pop()  # remove choice
