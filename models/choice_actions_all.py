from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from models.actions.base import Action
from models.choice_options import CO

if TYPE_CHECKING:
    from models.actions.ability_pipeline import AbilityPipeline
    from models.game_card.game_card import GameCard


# --- GENERIC CHOICE ACTIONS ---
@dataclass
class ChoiceAction(ABC):
    options: list[CO] = field(default_factory=list)
    may: bool = False
    on_complete: Callable[[], None] | None = None

    @dataclass
    class _Decline(Action):
        def __repr__(self):
            return 'Decline'

        def play(self) -> None:
            self.finish()

    def __post_init__(self):
        if self.may:
            self.options.append(CO(description='Decline', callback=lambda: None))
            # p_idx = self.options[0].player_idx
            # gs = self.options[0].gs
            # self.options.append(ChoiceAction._Decline(p_idx, gs))

    def choose_target(self, target):
        raise NotImplementedError

    def complete(self):
        if self.on_complete:
            self.on_complete()

    def get_actions(self) -> list[CO]:
        return self.options


class XChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    def get_actions(self) -> list[Action]:
        from models.actions.ability_pipeline_support import SelectXAction2
        min_x, max_x = self.pipeline.get_x_range()
        return [SelectXAction2(self.pipeline.player_idx, self.pipeline.gs, self.pipeline, x)
                for x in range(min_x, max_x + 1)]

class ModeChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    def get_actions(self) -> list[Action]:
        ...

class ExtraCostChoice2(ChoiceAction):
    def __init__(self, pipeline: AbilityPipeline):
        self.pipeline = pipeline

    def get_actions(self) -> list[Action]:
        ...
