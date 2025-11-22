from typing import Optional

from models.effects.base import Effect
from card_filter import CardFilter

def castle_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            # remove castle perm mods from source's pt_modifiers if present
            to_remove = [m for m in source.pt_modifiers if getattr(m.card, "props", None) and m.card.props.slug == 'castle']
            for m in to_remove:
                source.remove_perm_mod(m.card)
    return E()


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
