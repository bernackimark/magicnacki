from typing import Optional

from models.effects.base import Effect
from card_filter import CardFilter

def creature_bond_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            # creature leaving: for every attached aura that is creature-bond, do life loss to creature's owner
            for aura in list(target.auras):
                if aura.props.slug == 'creature-bond':
                    gs.decrement_life(target.orig_owner_id, target.props.toughness, aura)
    return E()

def crusade_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            # If a crusade permanent leaves, remove its perm mod from all white creatures.
            if source.props.slug == 'crusade':
                for white_creature in CardFilter(gs).in_play().creatures().white().result():
                    white_creature.remove_perm_mod(source)
    return E()

def default_clear_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            # default cleanup call (clear mods)
            source.clear_all_mods()
    return E()
