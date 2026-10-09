from .slug_effect_map_a_to_e import MAP as MAP1
from .slug_effect_map_f_to_o import MAP as MAP2
from .slug_effect_map_p_to_z import MAP as MAP3
from ..effects.base import EffSpec

"""Stitch together smaller slug-effect maps; one consolidated map created IDE performance issues during development;
Here are the different styles of EffSpec declarations:
 - Activated ...:
   - ex that costs {BRG}, {T}, its resolver is Bounce, activator selects from creatures in their gy via CardFilter:
   - ... Activated('BRGT', Bounce(), CF.creatures_in_your_graveyard())
 - GenTrig ... a generic trigger that implements a fluent pattern:
   - On accepts an event for which to listen
   - .where() accepts an EC() "event condition" which employs method chaining
   - .then() accepts a Resolver which will ultimately produce a ".resolve()" method
   - .modify() accepts a Modifier
   - ex: GenTrig(On(CombatEndEvent).where(EC().self_is_combatant()).then(DestroySelfCombatants()))
   - ex: On(DamageProposedEvent, 'EOT').
                                   where(EC().damage_target_in(CF.owner()).damage_source_in(CF.non_fliers())).
                                   modify(PreventDamage()).build()  <-- sometimes .build() is needed at the end
 - Register adds a Listener to GameState.EventManager:
   - ex: Register(CantBeTargetedByAuras, target_attr='protected_card')
 - Spell ... executes via its own .resolve() method:
   - ex with no targets: Spell(DestroyAll(CF.forests()))
   - ex with target (that kicks off a flow for target selection): Spell(Destroy(), CF.blue_permanents()) 
 - Static effects are always on:
   - ex: Static(CantBeTargetedByAuras(CF.host()))
   - ex: Static(PumpApplies(CF.black_creatures(), (1, 1)))
 - "Templates" can be used for implementations that are similar:
   - ex: dual_land_specs('BG')
   - ex: MANA_BATTERY_ADD_CHARGE
   - ex: mana_battery_add_mana('B')
   - ex: self_pump('W', 0, 1)
 - Triggered is the non-generic version of "GenTrig" :
   - ex: Triggered(AislingLeprechaun())
 - Do ... executes a series of Resolvers:
   - ex: Do(Reanimate(), Pump(-1, 0))

EffSpec accept various other parameters:
 - examples:
   - allowed_p_turn_func=CF.owner()
   - allowed_phases=[Phase.UPKEEP]
   - allowed_activators=A_FUNCS['all_players']
   - extra_costs=[SacCardCost(CF.your_creatures())]
   - is_mana_ability=True, )
   - max_activations_per_turn=1
   - text=f'Add {{{W}}}'
   - max_x_func=your_tapped_land_cnt_and_max_x)
"""

INVOCATIONS: dict[str, list[EffSpec]] = {}
INVOCATIONS.update(MAP1)
INVOCATIONS.update(MAP2)
INVOCATIONS.update(MAP3)
