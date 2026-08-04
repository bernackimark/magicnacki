from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.base import Action
from models.cost import Cost


@dataclass
class AbilityAction(Action):
    pipeline: AbilityPipeline

    def __repr__(self):
        pl = self.pipeline
        eff_text = pl.eff_spec.effect if pl.eff_spec else '[card only, no ability]'
        return f'Card/Ability on stack. Card: {pl.source} Ability: {eff_text} Target: {pl.targets}'

    def play(self) -> None:
        self.pipeline.resolve_ability()


@dataclass
class SelectXAction2(Action):
    pipeline: AbilityPipeline
    x: int

    def __repr__(self):
        return f'{self.pipeline}, X={self.x}'

    def play(self):
        self.pipeline.x_value = self.x
        self.pipeline.source.extras['x'] = self.x


@dataclass
class SelectTargetAction2(Action):
    pipeline: AbilityPipeline
    target: Any

    def __repr__(self):
        return f'{self.pipeline}, add target: {self.target}'

    def play(self):
        self.pipeline.targets.append(self.target)


@dataclass
class SelectExtraCostAction2(Action):
    pipeline: AbilityPipeline
    cost: Cost

    def __repr__(self):
        return f'{self.pipeline}, add cost: {self.cost}'

    def play(self) -> None:
        self.pipeline.selected_extra_costs.append(self.cost)
