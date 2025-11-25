from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum, Enum, auto
from typing import TYPE_CHECKING, Callable, Optional, Union

from phase_fsm import Phase
from utils import flip

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from card_filter import CardFilter
from models.modifiers import PTTemp, KWATemp

Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

@dataclass
class ActivatedAbility:
    """A Target can be: GameCard, list[GameCard], int (a single player's index), tuple[int, int] (both players' indices),
    None (I need review why this is needed by game_state.get_available_targets())
    """
    class AllowedPlayerTurn(Enum):
        CASTER = auto()
        OPPONENT = auto()

    card: "GameCard"
    cost_tap: bool
    cost_mana: str
    target_filter: Optional[Callable[[GameState, GameCard], Target]] = None
    effect: Callable[[GameState, GameCard, Target], None] = None
    allowed_phases: list[Phase] = field(default_factory=list)
    allowed_player_turns: list[AllowedPlayerTurn] = field(default_factory=list)

    def __post_init__(self):
        if not self.allowed_player_turns:
            self.allowed_player_turns = list(self.AllowedPlayerTurn)

    def _get_allowed_player_idx_turns(self) -> list[int]:
        allowed_p_idx_turns = []
        if self.AllowedPlayerTurn.CASTER in self.allowed_player_turns:
            allowed_p_idx_turns.append(self.card.orig_owner_id)
        if self.AllowedPlayerTurn.OPPONENT in self.allowed_player_turns:
            allowed_p_idx_turns.append(flip(self.card.orig_owner_id))
        return allowed_p_idx_turns

    def can_activate(self, gs: "GameState") -> bool:
        if self.cost_tap and self.card.is_tapped:
            return False
        if self.cost_mana and not gs.mana_pools[self.card.orig_owner_id].can_pay(self.cost_mana):
            return False
        if self.allowed_phases and gs.phase not in self.allowed_phases:
            return False
        if self.card.orig_owner_id not in self._get_allowed_player_idx_turns():
            return False
        return True


def psionic_entity_deals_damage(gs: "GameState", source: "GameCard", t: Target):
    source.deal_damage_to_player(gs, 2, t) if isinstance(t, int) else source.deal_damage_to_card(gs, 2, t)
    source.deal_damage_to_card(gs, 3, source)

def add_activated_abilities(cards: list["GameCard"]) -> None:
    for c in cards:
        if c.props.slug == 'apprentice-wizard':
            c.abilities.append(ActivatedAbility(c, True, 'U', target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add('C', 3)))
        if c.props.slug == 'blessing':
            c.abilities.append(ActivatedAbility(
                c, False, 'W', target_filter=None,
                effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 1))))
        if c.props.slug == 'brainwash':
            c.abilities.append(ActivatedAbility(c, False, '3', target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Attack'))))
        if c.props.slug == 'farmstead':
            c.abilities.append(ActivatedAbility(c, True, 'WW', target_filter=lambda gs, _: gs.player_turn_idx,
                               effect=lambda gs, _, t: gs.increment_life(gs.player_turn_idx, 1)))
        if c.props.slug == 'flood':
            c.abilities.append(ActivatedAbility(
                c, False, 'UU', target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().tapped(False).has('Flying', False).result(),
                                  effect=lambda gs, source, t: t.tap(gs)))
        if c.props.slug == 'holy-armor':
            c.abilities.append(ActivatedAbility(c, False, 'W', target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(0, 1))))
        if c.props.slug == 'northern-paladin':
            c.abilities.append(ActivatedAbility(
                c, True, 'WW', target_filter=lambda gs, source: CardFilter(gs).in_play().black().by_type(['Creature', 'Enchantment']).result(),
                                  effect=lambda gs, source, t: gs.send_to_graveyard_from_play(t)))
        if c.props.slug in ('pirate-ship', 'prodigal-sorcerer'):
            # damage to card
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: source.deal_damage_to_card(gs, 1, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, source, t: source.deal_damage_to_player(gs, 1, t)))
        if c.props.slug in ('psionic-entity'):
            # damage to card
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: psionic_entity_deals_damage(gs, source, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, True, '', target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, source, p_id: psionic_entity_deals_damage(gs, source, p_id)))
        if c.props.slug == 'wall-of-water':
            c.abilities.append(ActivatedAbility(c, False, 'U', target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 0))))


if __name__ == '__main__':
    ...
