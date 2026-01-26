from __future__ import annotations

from typing import Optional

from game_state import GameState
from models.effects.base import Effect
from models.game_card import GameCard
from models.modifiers import PTModifier, PTTemp, KWAModifier, KWATemp


def dragon_whelp_on_end_step():
    """If this [pump] ability has been activated four or more times this turn,
    sacrifice this creature at the beginning of the next end step.
    Note: this isn't technically correct code.  Because PTTemp doesn't store the source card, I'm counting all +1/+0s"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            cnt = len([temp for temp in s.modifiers.temps if temp.power_delta == 1 and temp.toughness_delta == 0])
            if cnt >= 4:
                gs.send_to_graveyard_from_play(s)
    return E()


def giant_tortoise_on_untap():
    class E(Effect):
        event = 'untap'

        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.modifiers.auras.append(PTModifier(source, 0, 3))
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


def kobold_drill_sergeant_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            kobolds = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
            for k in kobolds[:]:
                for mod in k.modifiers.auras:  # remove both the Trample and +0/+1
                    if mod.card == source:
                        k.modifiers.remove_aura(mod)
    return E()


def kobold_overlord_and_taskmaster_on_leave():
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


def blood_lust_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # Target creatures gain +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1.
            if target:
                new_toughness = max(1, target.toughness - 4)
                toughness_mod = new_toughness - target.toughness
                target.modifiers.auras.append(PTModifier(source, 4, toughness_mod))
    return E()


def divine_transformation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 3, 3))
    return E()


def giant_growth_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(PTTemp(3, 3))
    return E()


def giant_strength_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(PTModifier(source, 2, 2))
    return E()


def giant_tortoise_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            source.modifiers.auras.append(PTModifier(source, 0, 3))
    return E()


def great_defender_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            """Target creature gets +0/+X until end of turn, where X is its mana value."""
            if target:
                target.modifiers.auras.append(PTTemp(0, target.props.casting_weight))
    return E()


def holy_armor_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Holy armor didn't get a target!")
            if target:
                target.modifiers.auras.append(PTModifier(source, 0, 2))
    return E()


def holy_strength_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 1, 2))
    return E()


def howl_from_beyond_on_cast():
    """Target creature gets +X/+0 until end of turn"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            if target is not None:
                x = getattr(source, 'variable_x', 0)  # read X chosen when casting
                target.modifiers.temps.append(PTTemp(x, 0))
    return E()


def instill_energy_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Instill Energy needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Haste'))
    return E()


def jump_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.temps.append(KWATemp('add', 'Flying'))
    return E()


def immolation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 2, -2))
    return E()


def unholy_strength_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 2, 1))
    return E()


def unstable_mutation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 3, 3))
    return E()


def weakness_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, -2, -1))
    return E()


def kobold_taskmaster_on_cast():
    """Other Kobold creatures you control get +1/+0"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for t in gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result():
                if source != t:
                    t.modifiers.auras.append(PTModifier(source, 1, 0))
    return E()
