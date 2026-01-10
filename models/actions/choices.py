from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

from constants import COLOR_LETTERS_W_COLORLESS

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action
from models.actions.choice import ChoiceAction

# --- GENERIC ACTIONS ---
class AddMana(Action):
    def __init__(self, p_id, gs, source: GameCard, color: str, amt: int = 1):
        super().__init__(p_id, gs)
        self.source = source
        self.color = color
        self.amt = amt

    def __repr__(self):
        return f'Add {self.amt} {self.color} to your mana pool'

    def play(self):
        self.gs.mana_pools[self.player_idx].add_floating(self.color, self.amt)

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

# --- GENERIC CHOICE ACTIONS ---
class AddManaOfColorChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard,
                 possible_colors: Iterable[str] = COLOR_LETTERS_W_COLORLESS, amt: int = 1):
        super().__init__(p_id, gs, source)
        self.possible_colors = possible_colors
        self.amt = amt

    def get_actions(self) -> list[Action]:
        return [AddMana(self.p_id, self.gs, self.source, color, self.amt) for color in self.possible_colors]

class PayManaOrSacUpkeepChoice(ChoiceAction):
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

class ErosionUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.p_id].can_pay('1'):
            actions.append(PayMana(self.p_id, self.gs, self.source, '1'))
        actions.append(PayLife(self.p_id, self.gs, self.source, 1))
        actions.append(Sac(self.p_id, self.gs, self.source.attached_to))
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

class LordOfThePitUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        your_other_creatures = [c for c in self.gs.card_filter.on_player_board(self.gs.player_turn_idx).creatures().result() if c != self.source]
        if not your_other_creatures:
            return []
        return [Sac(self.gs.player_turn_idx, self.gs, c) for c in your_other_creatures]

class SeasonOfTheWitchUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayLife(self.source.attached_to.orig_owner_id, self.gs, self.source, 2),
                Sac(self.gs.player_turn_idx, self.gs, self.source)]
