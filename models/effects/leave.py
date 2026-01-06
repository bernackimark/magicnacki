from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from models.modifiers import KWAModifier, PTModifier
from card_filter import CardFilter

"""Effects for when cards leave the playing field (ex Castle, Crusade)"""

def global_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            for e in gs.global_effects:
                if source == e[0]:
                    gs.global_effects.remove(e)
                    break
    return E()

def akron_legionnaire_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack
            my_creatures: list[GameCard] = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
            for my_creature in my_creatures:
                for aura in my_creature.modifiers.auras:
                    if aura.props.slug == 'akron-legionnaire':
                        my_creature.modifiers.auras.remove(aura)
                        break
    return E()

def creature_bond_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: i think this is wrong; i think it's only if creature goes to graveyard
            # creature leaving: for every attached aura that is creature-bond, do life loss to creature's owner
            for aura in target.modifiers.auras:
                if aura.props.slug == 'creature-bond':
                    gs.decrement_life(target.orig_owner_id, target.props.toughness, aura)
    return E()

def evil_eye_of_orms_by_gore_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            """Non-Eye creatures you control can't attack."""
            my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
            for my_creature in my_creatures:
                for aura in my_creature.modifiers.auras:
                    if aura.props.slug == 'evil-eye-of-orms-by-gore':
                        my_creature.modifiers.auras.remove(aura)
                        break
    return E()

def forest_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            for c in gs.card_filter.on_player_board(s).by_slug('kird-ape').result():
                if len(gs.card_filter.on_player_board(s).by_slug('forest').result()) == 1:  # should this be 0 or 1?
                    for mod in c.modifiers.auras:
                        if mod == PTModifier(c, 1, 2):
                            c.modifiers.remove_aura(mod)
    return E()

def goblin_king_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Goblin').result()
            for t in targets[:]:
                for mod in t.modifiers.auras:  # remove both the Mountainwalk and +1/+1
                    if mod.card == source:
                        t.modifiers.remove_aura(t)
    return E()

def island_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """If out of islands, send all of your creatures with Islandhome to the graveyard"""
            p_id = source.orig_owner_id
            my_islands = CardFilter(gs).on_player_board(p_id).by_slug('island').result()
            if len(my_islands) > 1:
                return
            my_island_home_creatures = CardFilter(gs).on_player_board(p_id).has('Islandhome').result()
            for creature in my_island_home_creatures:
                gs.send_to_graveyard_from_play(creature)
    return E()

def kobold_overlord_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
            for t in targets[:]:
                for mod in t.modifiers.auras:
                    if mod.card == source:
                        t.modifiers.remove_aura(t)
                        break
    return E()

def lord_of_atlantis_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Merfolk').result()
            for t in targets[:]:
                for mod in t.modifiers.auras:  # remove both the Islandwalk and +1/+1
                    if mod.card == source:
                        t.modifiers.remove_aura(t)
    return E()

def default_clear_on_leave():
    class E(Effect):
        event = 'leave'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            ...
            # TODO: should this remove cards from board?
    return E()
