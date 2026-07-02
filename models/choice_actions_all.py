from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.actions.base import Action
    from models.game_card.game_card import GameCard
    from models.effects.base import EffSpec, ActivatedAbility


# --- GENERIC CHOICE ACTIONS ---
@dataclass
class ChoiceAction(ABC):
    options: list[Action | None] = field(default_factory=list)

    def get_actions(self) -> list[Action]:
        return self.options


# SINCE THIS TRACKS STATE (selected targets), THIS IS A WORTHY DESCENDENT OF CHOICE ACTION
class MultiTargetChoice(ChoiceAction):
    """Used if an effect calls for multiple targets; is a container for the selected targets"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard, eff_spec: EffSpec,
                 x_value_for_variable_cast: int | None = None):
        self.player_idx = p_id
        self.gs = gs
        self.source = source
        self.eff_spec = eff_spec
        self.x_value_for_variable_cast = x_value_for_variable_cast
        self.selected_targets = []

    def get_actions(self) -> list[Action]:
        from models.actions.target import AddTargetAction, FinishTargetsAction
        actions = []
        target_spec = self.eff_spec.target_spec
        candidates = target_spec.filter_func(self.gs, self.source)

        if target_spec.max_cnt is None or len(self.selected_targets) < target_spec.max_cnt:
            for c in candidates:
                if ((c not in self.selected_targets or self.eff_spec.target_spec.allow_duplicate_targets)
                        and self.gs.perm_querier.can_target(c, self.source)):
                    actions.append(AddTargetAction(self.player_idx, self.gs, self, c))

        if len(self.selected_targets) >= target_spec.min_cnt:
            actions.append(FinishTargetsAction(self.player_idx, self.gs, self))

        return actions


# THIS ENTIRE CLASS IS BEING PASSED DOWNSTREAM TO THE ACTION, BUT DOES THIS MAKE ANY SENSE?
class XValueChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, x_options: list[int],
                 eff_spec: EffSpec, aa: ActivatedAbility = None):
        self.player_idx = p_id
        self.gs = gs
        self.source = source
        self.x_options = x_options
        self.eff_spec = eff_spec
        self.aa = aa

    def get_actions(self) -> list[Action]:
        from models.actions.special import SelectXAction
        return [SelectXAction(self.player_idx, self.gs, self, x) for x in self.x_options]

