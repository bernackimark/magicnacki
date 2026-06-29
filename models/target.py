from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


def create_target_text(targets: int | "GameCard" | tuple | list | None):
    from models.game_card.game_card import GameCard
    """0 -> ', targeting Player #0' ... [1, c1] -> ', targeting Player #1, Air Elemental'
    (0, 1) -> ', targeting Player #0, Player #1' ... [c1, c2] -> , 'targeting Air Elemental, Savannah Lions'"""
    from models.game_card.game_card import GameCard
    if not targets:
        return ''
    if isinstance(targets, int):
        return f', targeting Player #{targets}'
    if isinstance(targets, GameCard):
        return ', targeting ' + targets.props.name
    begin_text = ', targeting'
    target_texts = []
    for t in targets:
        target_text = t.props.name if isinstance(t, GameCard) else f'Player #{t}'
        target_texts.append(target_text)
    return f"{begin_text} {', '.join(target_texts)}"


@dataclass
class TargetSpec:
    filter_func: Callable
    min_cnt: int = 1
    max_cnt: int | None = 1
    allow_duplicate_targets: bool = False  # used in pyrotechnics/fireball where we always add 1 damage at a time

    def get_targets(self, gs: "GameState", source: "GameCard") -> list["GameCard" | int | None]:
        """Execute the effect's filter func;
        If target is an int, let it through; if target is a GameCard, check can_target();
        If there are enough targets, return all targets, else return []"""
        from models.game_card.game_card import GameCard
        candidates: list[GameCard] | list[int] | list[GameCard | int] | GameCard | int = self.filter_func(gs, source)
        legal_targets = []
        if isinstance(candidates, int):
            return [candidates]
        if isinstance(candidates, GameCard):
            return [candidates] if gs.perm_querier.can_target(candidates, source) else []
        for c in candidates:
            if isinstance(c, int):
                legal_targets.append(c)
                continue
            if gs.perm_querier.can_target(c, source):
                legal_targets.append(c)
        return legal_targets if len(legal_targets) >= self.min_cnt else []
