from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.modifiers import KWAMod


class AddKWA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, target: GameCard, ability: str, until_eot: bool = True):
        super().__init__(p_id, gs)
        self.source = s
        self.target = target
        self.ability = ability
        self.until_eot = until_eot

    def __repr__(self):
        return f'Give {self.ability} to {self.target.props.name}'

    def play(self):
        self.target.modifiers.append(KWAMod(s=self.source, item=self.ability,
                                            expires='EOT' if self.until_eot else None))
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        else:
            self.gs.action_stack.pop()

class JohanAction(Action):
    """At your combat begin step, you may have J gain Defender & your creatures gain Vigilance EOT.
    If J becomes tapped, your creatures lose their Vigilance."""
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return f'{self.source.props.name} gains Defender & your creatures gain Vigilance until end of turn'

    def play(self) -> None:
        from models.effects.listeners_tap_untap import JohanOnTap
        self.source.modifiers.append(KWAMod(s=self.source, item='Defender', expires='EOT'))
        for c in self.gs.card_filter.on_player_board(self.source.owner_id).creatures().result():
            c.modifiers.append(KWAMod(s=self.source, item='Vigilance', expires='EOT'))
        self.gs.event_mgr.register(JohanOnTap(), self.source)
