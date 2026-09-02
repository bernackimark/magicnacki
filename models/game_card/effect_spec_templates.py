from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar, Generic, Callable

if TYPE_CHECKING:
    from models.effects.base import Resolver
    from models.game_card.game_card import GameCard

from models.cost import RemoveCounterCost
from models.effects.listeners_generic import GenericEventListener
from models.events_all import Event
from models.game_card.counter_tokens import CHARGE, PIN, PLUS_ONE_ZERO
from models.effects.base import EffSpec, Activated
from models.effects.resolvers_generic import AddMana, AddCounter, ManaBatteriesAddMana, Pump
from models.game_card.card_filter_funcs import TF
from models.systems.mana import ManaCost

E = TypeVar("E", bound=Event)

class On(Generic[E]):
    """Fluent builder for a trigger & a resolver"""
    def __init__(self, event_type: type[E]):
        self.event_type = event_type
        self.conditions: list[Callable[[E, GameCard], bool]] = []
        self.resolver = None
        self.modifier = None  # Event modifier (event.remaining [damage], event.permission [queries], etc)

    def where(self, *conditions) -> "On[E]":
        self.conditions.extend(conditions)
        return self

    def then(self, resolver: Resolver):
        self.resolver = resolver
        return self

    # THIS IS THE NEW FUNCTIONALITY SPECIFIC FOR MODIFIYING AN EVENT (event.remaining, event.permission, etc.)
    def modify(self, modifier):
        self.modifier = modifier
        return self

    def build(self) -> GenericEventListener:
        return GenericEventListener(event_type=self.event_type, conditions=self.conditions,
                                    resolver=self.resolver, modifier=self.modifier)


# --- HELPERS THAT BUILD EFFSPEC ---
def dual_land_specs(colors: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), TF.owner(), is_mana_ability=True,
                      text=f'Add {{{color}}}') for color in colors]

def self_pump(activation_cost: str, p: int, t: int):
    """Returns an Activated EffSpec; it is EOT=True, target is the card itself"""
    return Activated(activation_cost, Pump(power_adj=p, toughness_adj=t, eot=True), TF.self(),
                     text=f'Pump +{p}/+{t}')

def mana_battery_add_mana(color: str) -> EffSpec:
    return Activated('T', ManaBatteriesAddMana(color), extra_costs=[RemoveCounterCost(CHARGE)], is_mana_ability=True,
                     max_x_func=lambda gs, s: TF.self()(gs, s).counters.get_count(CHARGE),
                     text=f'Remove any number of charge counters from this artifact: Add {color}, '
                          f'then add an additional {color} for each charge counter removed this way')

def mox_specs(color: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), TF.owner(), is_mana_ability=True, text=f'Add {{{color}}}')]


MANA_BATTERY_ADD_CHARGE = Activated('2T', AddCounter(CHARGE), TF.self())


# --- X HELPERS ---
def clockwork_avian_x(_, s):
    return 4 - s.counters.get_count(PLUS_ONE_ZERO)

def clockwork_beast_x(_, s):
    return 7 - s.counters.get_count(PLUS_ONE_ZERO)

def max_x_from_printed_card(gs, s):
    return gs.mana_pools[s.owner_id].get_max_x(s.casting_cost) // s.casting_cost.count('X')

def target_spell_mv(gs, _):
    from models.actions.ability_pipeline_support import AbilityAction
    spell = gs.action_stack.last_action
    cost = spell.pipeline.total_ability_cost if isinstance(spell, AbilityAction) else spell.source.casting_cost
    cost_int = sum(ManaCost(cost).decoded.values())
    return cost_int

def your_tapped_land_cnt_and_max_x(gs, s):
    your_tapped_land_cnt = len(gs.card_filter.on_player_board(s.owner_id).tapped().lands().result())
    produceable_mana_cnt = gs.mana_pools[s.owner_id].get_max_x('')
    return min(your_tapped_land_cnt, produceable_mana_cnt)

def voodoo_doll_x(_, source):
    return source.counters.get_count(PIN) // 2
