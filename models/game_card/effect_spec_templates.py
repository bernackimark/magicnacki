from models.cost import RemoveCounterCost
from models.counter_tokens import CHARGE, PIN, PLUS_ONE_ZERO
from models.effects.base import EffSpec, Activated
from models.effects.resolvers_generic import AddMana, UntapForManaEffect, AddCounter, ManaBatteriesAddMana, Pump
from models.game_card.card_filter_funcs import T_FUNCS
from models.phase_manager import Phase


def dual_land_specs(colors: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), T_FUNCS['card_owner'], text=f'Add {{{color}}}') for color in colors]

def self_pump(activation_cost: str, p: int, t: int):
    """Returns an Activated EffSpec; it is EOT=True, target is the card itself"""
    return Activated(activation_cost, Pump(power_adj=p, toughness_adj=t, eot=True), T_FUNCS['self'],
                     text=f'Pump +{p}/+{t}')

def untap_for_mana_at_owner_upkeep(untap_cost: str, owner_id: int) -> EffSpec:
    return Activated(untap_cost, UntapForManaEffect(untap_cost), allowed_phases=[Phase.UPKEEP],
                     allowed_p_id_turn=owner_id, text='Untap')

def mana_battery_add_mana(color: str) -> EffSpec:
    return Activated('T', ManaBatteriesAddMana(color), extra_costs=[RemoveCounterCost(CHARGE)],
                     max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE),
                     text=f'Remove any number of charge counters from this artifact: Add {color}, '
                          f'then add an additional {color} for each charge counter removed this way')

def mox_specs(color: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), T_FUNCS['card_owner'], text=f'Add {{{color}}}')]


MANA_BATTERY_ADD_CHARGE = Activated('2T', AddCounter(CHARGE), T_FUNCS['self'])


# --- X HELPERS ---
def clockwork_avian_x(_, s):
    return 4 - s.counters.get_count(PLUS_ONE_ZERO)

def clockwork_beast_x(_, s):
    return 7 - s.counters.get_count(PLUS_ONE_ZERO)

def max_x_from_printed_card(gs, s):
    return gs.mana_pools[s.owner_id].get_max_x(s.casting_cost)

def voodoo_doll_x(_, source):
    return source.counters.get_count(PIN) // 2

