from models.counter_tokens import CHARGE
from models.effects.base import EffSpec, Activated
from models.effects.resolvers_generic import AddMana, UntapForManaEffect, UntapHostForManaEffect, AddCounter
from models.game_card.card_filter_funcs import T_FUNCS
from models.phase_manager import Phase


def dual_land_activated_ability_specs(colors: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), T_FUNCS['card_owner'], text=f'Add {{{color}}}') for color in colors]


def untap_for_mana_at_owner_upkeep(untap_cost: str, owner_id: int) -> EffSpec:
    return Activated(untap_cost, UntapForManaEffect(untap_cost), allowed_phases=[Phase.UPKEEP],
                     allowed_p_id_turn=owner_id, text='Untap')


MANA_BATTERY_ADD_CHARGE = Activated('2T', AddCounter(CHARGE), T_FUNCS['self'])
