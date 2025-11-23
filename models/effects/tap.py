from typing import Optional

from models.effects.base import Effect
from card_filter import CardFilter

def giant_tortoise_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.remove_perm_mod(source)
    return E()


def psychic_venom_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if any(a.props.slug == "psychic-venom" for a in source.auras):
                gs.decrement_life(source.orig_owner_id, 2, source)
    return E()
