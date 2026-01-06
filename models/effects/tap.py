from typing import Optional, TYPE_CHECKING

from models.effects.base import Effect
from card_filter import CardFilter
from utils import flip

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

def tap_for_mana(color: str):
    class E(Effect):
        event = 'tap'

        def resolve(self, gs, source, target=None):
            raise NotImplementedError("Handling mana in a different way")
            # current approach is to not tap land to generate mana, but instead,
            # pre-calculate the mana needed and tap down from there
            # will probably need to change this if moving to a user-selects-their-own-mana-source system
            # gs.mana_pools[source.orig_owner_id].add_floating(color)
    return E()

def forest_on_tap():
    """lifetap: Enchantment UU [] Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    class E(Effect):
        event = 'tap'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            for _ in gs.card_filter.on_player_board(flip(s.orig_owner_id)).by_slug('lifetap').result():
                gs.increment_life(flip(s.orig_owner_id), 1)
    return E()

def giant_tortoise_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.modifiers.remove_aura(source)
    return E()

def mountain_on_tap():
    """"lifeblood": Enchantment 2WW [] Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    class E(Effect):
        event = 'tap'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            for _ in gs.card_filter.on_player_board(flip(s.orig_owner_id)).by_slug('lifeblood').result():
                gs.increment_life(flip(s.orig_owner_id), 1)
    return E()

def psychic_venom_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if any(a.props.slug == "psychic-venom" for a in source.modifiers.auras):
                gs.decrement_life(source.orig_owner_id, 2, source)
    return E()
