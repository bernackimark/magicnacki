from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action
from models.actions.choice import ChoiceAction

# --- GENERICS ---
class DealDamage(Action):
    def __init__(self, p_id, gs, source: GameCard, damage_amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.damage_amt = damage_amt

    def __repr__(self):
        return f'{self.source.props.name} deals {self.damage_amt} damage to you'

    def play(self):
        self.gs.apply_damage(self.source, self.damage_amt, self.source.orig_owner_id)
        self.gs.action_stack.pop()  # remove choice

class PayMana(Action):
    def __init__(self, p_id, gs, source: GameCard, cost: str):
        super().__init__(p_id, gs)
        self.source = source
        self.cost = cost

    def __repr__(self):
        return f'Pay {self.cost} for {self.source.props.name}'

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.cost)
        self.gs.action_stack.pop()

class PayLife(Action):
    def __init__(self, p_id, gs, source: GameCard, amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.amt = amt

    def __repr__(self):
        return f'Pay {self.amt} life for {self.source.props.name}'

    def play(self):
        self.gs.apply_damage(self.source, self.amt, self.source.attached_to.orig_owner_id)
        self.gs.action_stack.pop()

class Sac(Action):
    def __init__(self, p_id, gs, source: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.source = source
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Sacrifice {self.source.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.source, self.w_damage_amt, self.source.orig_owner_id)
        self.gs.send_to_graveyard_from_play(self.source)
        self.gs.action_stack.pop()  # remove choice

class PayOrSacUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cost: str):
        super().__init__(p_id, gs, source)
        self.cost = cost

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.p_id].can_pay(self.cost):
            actions.append(PayMana(self.p_id, self.gs, self.source, self.cost))
        actions.append(Sac(self.p_id, self.gs, self.source))
        return actions

# --- CARD-SPECIFIC ---

class CosmicHorrorUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cost: str):
        super().__init__(p_id, gs, source)
        self.cost = cost

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.p_id].can_pay(self.cost):
            actions.append(PayMana(self.p_id, self.gs, self.source, self.cost))
        actions.append(Sac(self.p_id, self.gs, self.source, 7))
        return actions

class CurseArtifactUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        # warning: Curse Artifact is usually played on opp cards and that's a mismatch on "orig_owner_id"
        return [PayLife(self.source.attached_to.orig_owner_id, self.gs, self.source, 2),
                Sac(self.source.attached_to.orig_owner_id, self.gs, self.source.attached_to)]

class ElderSpawnUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        for island in self.gs.card_filter.on_player_board(self.p_id).by_slug('island').result():
            actions.append(Sac(self.p_id, self.gs, island))
        actions.append(Sac(self.p_id, self.gs, self.source, 6))
        return actions

class ForceOfNatureUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, cost: str, damage_amt: int):
        super().__init__(p_id, gs, source)
        self.cost = cost
        self.damage_amt = damage_amt

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.p_id].can_pay(self.cost):
            actions.append(PayMana(self.p_id, self.gs, self.source, self.cost))
        actions.append(DealDamage(self.p_id, self.gs, self.source, self.damage_amt))
        return actions
