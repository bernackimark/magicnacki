from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.events_all import DamageProposedEvent
    from models.game_card.game_card import GameCard

from models.actions.base import Action

class DealDamageTo(Action):
    def __init__(self, p_id, gs, source: GameCard, damage_amt: int, target: GameCard | int):
        super().__init__(p_id, gs)
        self.source = source
        self.damage_amt = damage_amt
        self.target = target

    def __repr__(self):
        return f'{self.source.props.name} deals {self.damage_amt} damage to {self.target}'

    def play(self) -> None:
        self.gs.apply_damage(self.source, self.damage_amt, self.target)
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        if self.gs.pending_choice:
            self.gs.pending_choice = None

class DealDamageToYou(Action):
    def __init__(self, p_id, gs, source: GameCard, damage_amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.damage_amt = damage_amt

    def __repr__(self):
        return f'{self.source.props.name} deals {self.damage_amt} damage to you'

    def play(self):
        self.gs.apply_damage(self.source, self.damage_amt, self.source.owner_id)
        self.gs.action_stack.pop()  # remove choice

class GainLife(Action):
    def __init__(self, p_id, gs, source: GameCard, amt: int, target_p_id: int):
        super().__init__(p_id, gs)
        self.source = source
        self.amt = amt
        self.target_p_id = target_p_id

    def __repr__(self):
        return f'Player #{self.target_p_id} gains {self.amt} life from {self.source.props.name}'

    def play(self):
        self.gs.score_mgr.increment_life(self.target_p_id, self.amt, self.source, self.gs)
        self.gs.action_stack.pop()

class PayLife(Action):
    def __init__(self, p_id, gs, source: GameCard, amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.amt = amt

    def __repr__(self):
        return f'Pay {self.amt} life for {self.source.props.name}'

    def play(self):
        self.gs.apply_damage(self.source, self.amt, self.source.owner_id)
        if self.gs.action_stack:
            self.gs.action_stack.pop()
        elif self.gs.pending_choice:
            self.gs.pending_choice = None

class RedirectDamageToYouAction(Action):
    def __init__(self, p_id, gs, source: GameCard, event: DamageProposedEvent):
        super().__init__(p_id, gs)
        self.source = source
        self.event = event

    def __repr__(self):
        return f'Redirect all damage from {self.event.target} to you'

    def play(self) -> None:
        self.event.target = self.source.owner_id
        self.gs.pending_choice = None
