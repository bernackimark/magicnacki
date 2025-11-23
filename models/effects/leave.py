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


def castle_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            for e in gs.global_effects:
                if source == e[0]:
                    gs.global_effects.remove(e)
                    break
    return E()

def crusade_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            for e in gs.global_effects:
                if source == e[0]:
                    gs.global_effects.remove(e)
                    print("Removing Crusade from gs.global_effects")
                    break
    return E()

def default_clear_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            ...
            # gs.send_to_graveyard_from_play(source)  # removes from board; appends to graveyard
            # for a in source.auras:
            #     gs.send_to_graveyard_from_play(a)
            # source.clear_all_mods()
    return E()
