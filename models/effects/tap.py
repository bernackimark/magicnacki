from typing import Optional

from models.effects.base import Effect
from card_filter import CardFilter


def tap_for_mana(color: str):
    class E(Effect):
        event = 'tap'

        def resolve(self, gs, source, target=None):
            raise NotImplementedError("Handling mana in a different way")
            # current approach is to not tap land to generate mana, but instead,
            # pre-calculate the mana needed and tap down from there
            # will probably need to change this if moving to a user-selects-their-own-mana-source system
            ...
            # gs.mana_pools[source.orig_owner_id].add_floating(color)
    return E()

def giant_tortoise_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.modifiers.remove_aura(source)
    return E()

def psychic_venom_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if any(a.props.slug == "psychic-venom" for a in source.modifiers.auras):
                gs.decrement_life(source.orig_owner_id, 2, source)
    return E()
