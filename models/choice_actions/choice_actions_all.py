from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

from constants import COLOR_LETTERS_W_COLORLESS
from models.actions.damage import DealDamage, PayLife
from models.actions.destroy_sac_regen import Sac
from models.actions.mana import AddMana, PayMana
from models.actions.pump import VariablePTMod
from models.actions.special import SacCreatureAndAddMana, PayManaForLife, SkipDrawPhaseGainLife, SacTwoIslands
from models.actions.tap_untap import UntapCardStackPop, LeaveTapped, UntapWithManaAction

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action, DoNothing
from models.choice_actions.base import ChoiceAction


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

class PayManaToDrawCardsChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayManaToDrawCardsChoice(self.p_id, self.gs, self.source), DoNothing(self.p_id, self.gs)]

class PayOneColorlessForOneLifeChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayManaForLife(self.p_id, self.gs, '1', 1), DoNothing(self.p_id, self.gs)]

class SacALandChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        p_id = self.gs.player_turn_idx
        return [Sac(self.p_id, self.gs, c) for c in self.gs.card_filter.on_player_board(p_id).lands.result()]

class SacYourCreatureChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        p_id = self.gs.player_turn_idx
        return [Sac(self.p_id, self.gs, c) for c in self.gs.card_filter.on_player_board(p_id).creatures().result()]

class UntapChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [LeaveTapped(self.p_id, self.gs, self.source), UntapCardStackPop(self.p_id, self.gs, self.source)]

class UntapWithManaChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, mana_cost: str):
        super().__init__(p_id, gs, source)
        self.mana_cost = mana_cost

    def get_actions(self) -> list[Action]:
        return [LeaveTapped(self.p_id, self.gs, self.source),
                UntapWithManaAction(self.p_id, self.gs, self.source, self.mana_cost)]

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
        # warning: Curse Artifact is usually played on opp cards and that's a mismatch on "orig_owner_id" !!!
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

class FastingChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [SkipDrawPhaseGainLife(self.p_id, self.gs, 2), Sac(self.p_id, self.gs, self.source)]

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

class LeviathanUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        your_island_cnt = len([i for i in self.gs.card_filter.on_player_board(self.p_id).by_slug('island').result()])
        if your_island_cnt < 2:
            return []
        return [LeaveTapped(self.p_id, self.gs, self.source), SacTwoIslands(self.p_id, self.gs, self.source)]

class LordOfThePitUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        your_other_creatures = [c for c in self.gs.card_filter.on_player_board(self.p_id).creatures().result()
                                if c != self.source]
        if not your_other_creatures:
            return []
        return [Sac(self.gs.player_turn_idx, self.gs, c) for c in your_other_creatures]

class SacrificeCastChoice(ChoiceAction):
    """This is used by the card named 'Sacrifice'; is not a generic class about the concept of sacrifice"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        p_id = self.gs.player_turn_idx
        return [SacCreatureAndAddMana(self.p_id, self.gs, self.source, c, 'B', c.props.casting_weight)
                for c in self.gs.card_filter.on_player_board(p_id).creatures().result()]

class SeasonOfTheWitchUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [PayLife(self.source.attached_to.orig_owner_id, self.gs, self.source, 2),
                Sac(self.gs.player_turn_idx, self.gs, self.source)]

class SerendibDjinnUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [Sac(self.gs.player_turn_idx, self.gs, land, w_damage_amt=3 if land.props.slug == 'island' else 0)
                for land in self.gs.card_filter.on_player_board(self.gs.player_turn_idx).lands().result()]

class ShapeshifterChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        return [VariablePTMod(self.p_id, self.gs, self.source, self.source, i, 7 - i) for i in range(8)]
