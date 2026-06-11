from __future__ import annotations
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.counter_tokens import CounterType, CHARGE
from models.effects.base import EffSpec, Activated
from models.effects.resolvers_generic import AddMana, UntapForManaEffect, UntapHostForManaEffect, AddCounter
from models.game_card.card_filter_funcs import T_FUNCS
from models.phase_manager import Phase


def dual_land_activated_ability_specs(colors: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), T_FUNCS['card_owner'], text=f'Add {{{color}}}') for color in colors]


def untap_for_mana_at_owner_upkeep(untap_cost: str) -> EffSpec:
    return Activated(untap_cost, UntapForManaEffect(untap_cost), allowed_phases=[Phase.UPKEEP],
                     allowed_player_turn=EffSpec.AllowedPlayerTurn.CASTER, text='Untap')


def untap_host_for_mana_at_opp_upkeep(untap_cost: str) -> EffSpec:
    return Activated(untap_cost, UntapHostForManaEffect(untap_cost), allowed_phases=[Phase.UPKEEP],
                     allowed_player_turn=EffSpec.AllowedPlayerTurn.OPPONENT, text='Untap')


def is_tapped(s: GameCard) -> bool:
    return s.is_tapped


def has_ge_x_counters(card_func: Callable, counter_type: CounterType, min_cnt: int) -> bool:
    ...


MANA_BATTERY_ADD_CHARGE = Activated('2T', AddCounter(CHARGE), T_FUNCS['self'])
