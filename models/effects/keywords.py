from __future__ import annotations

from typing import Optional

from card_filter import CardFilter
from game_state import GameState
from models.actions.choices import AddKWA
from models.effects.base import Effect
from models.game_card import GameCard
from models.modifiers import KWAModifier
from utils import flip


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


def erhnam_djinn_on_upkeep():
    """At upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            opp_id = flip(source.orig_owner_id)
            for c in gs.card_filter.on_player_board(opp_id).non_wall_creatures().result():
                gs.action_stack.push(AddKWA(opp_id, gs, source, c, 'Forestwalk'))
    return E()


def akron_legionnaire_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack
            my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
            artifact_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_color('C').result()
            akron_legionnaires = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_slug(
                'akron-legionnaire').result()
            for my_creature in my_creatures:
                if my_creature not in [artifact_creatures + akron_legionnaires]:
                    my_creature.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))
    return E()


def animate_wall_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Defender'))
    return E()


def brainwash_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))
    return E()


def burrowing_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Mountainwalk'))
    return E()


def demonic_torment_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Demonic Torment needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))

    return E()


def eternal_warrior_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Eternal Warrior needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Vigilance'))
    return E()


def evil_eye_of_orms_by_gore_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            """Non-Eye creatures you control can't attack."""
            my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
            my_eyes = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_sub_type('Eye').result()
            for my_creature in my_creatures:
                if my_creature not in my_eyes:
                    my_creature.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))
    return E()


def flight_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Flying'))
    return E()


def fishliver_oil_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Fishliver Oil needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Islandwalk'))
    return E()


def kobold_overlord_on_cast():
    """Other Kobold creatures you control have first strike"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
            for t in targets:
                if source != t:
                    t.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))
    return E()


def lance_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))
    return E()
