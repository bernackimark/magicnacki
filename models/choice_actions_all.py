from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.actions.ability_pipeline import AbilityPipeline
    from models.actions.base import Action
    from models.game_card.game_card import GameCard


# --- GENERIC CHOICE ACTIONS ---
@dataclass
class ChoiceAction(ABC):
    options: list[Action | None] = field(default_factory=list)

    def choose_target(self, target):
        raise NotImplementedError

    def get_actions(self) -> list[Action]:
        return self.options


class XChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    def get_actions(self) -> list[Action]:
        from models.actions.ability_pipeline_support import SelectXAction2
        min_x, max_x = self.pipeline.get_x_range()
        return [SelectXAction2(self.pipeline.p_id, self.pipeline.gs, self.pipeline, x) for x in range(min_x, max_x + 1)]

class ModeChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    def get_actions(self) -> list[Action]:
        ...

class TargetChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    @property
    def targets(self) -> list[GameCard]:
        return [a.target for a in self.get_actions()]

    def choose(self, target):
        for action in self.get_actions():
            if action.target is target:
                action.play()
                return

    def get_actions(self) -> list[Action]:
        from models.actions.ability_pipeline_support import SelectTargetAction2
        p = self.pipeline
        targets = p.eff_spec.target_spec.get_targets(p.gs, p.source)
        return [SelectTargetAction2(p.p_id, p.gs, p, target) for target in targets]

class ExtraCostChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    def get_actions(self) -> list[Action]:
        ...
