from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.choices import SerendibDjinnUpkeepChoice, ShapeshifterChoice
from models.actions.special import SacCreatureAndAddMana
from models.counter_tokens import PUPA, PLUS_ONE, SLEEP
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.effects.damage import all_damage_prevented_to_target_card
from models.modifiers import KWAModifier, PTModifier, PTTemp
from utils import flip


def cocoon_on_upkeep():
    """At your upkeep, remove a pupa counter from this Aura.
    If you can't, sac it, put a +1/+1 counter on enchanted creature, and that creature gains flying."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            p_id = gs.player_turn_idx
            host = source.attached_to
            if p_id != source.orig_owner_id:
                return
            if not host.counters.get_count(PUPA):
                gs.send_to_graveyard_from_play(source)
                host.counters.add_counter(PLUS_ONE)
                host.modifiers.auras.append(KWAModifier(source, 'add', 'Flying'))
                return
            host.counters.remove_counter(PUPA)
    return E()


def serendib_djinn_on_upkeep():
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(SerendibDjinnUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()


def shapeshifter_on_upkeep():
    """At your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.action_stack.push(ShapeshifterChoice(source.orig_owner_id, gs, source), gs, False)
    return E()


def active_volcano_on_cast():
    """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
            gs.return_to_hand_from_board(t) if t.props.slug == 'island' else gs.send_to_graveyard_from_play(t)

    return E()


def animate_dead_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: GameCard = None):
            if not target:
                raise RuntimeError(f'{source.props.name} needs a target')
            card = gs.remove_from_your_graveyard(target, source.orig_owner_id)
            gs.boards[source.orig_owner_id].play_to_board(card)
            target.modifiers.auras.append(PTModifier(source, -1, 0))
    return E()


def crumble_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                gs.send_to_graveyard_from_play(target)
                gs.increment_life(target.orig_owner_id, target.props.casting_weight)
    return E()


def divine_offering_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Divine Offering needs a target")
            if target:
                gs.increment_life(source.orig_owner_id, target.power)
                gs.send_to_graveyard_from_play(target)
    return E()


def earthbind_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'remove', 'Flying'))
            if 'Flying' in target.keyword_abilities:
                gs.decrement_life(target.orig_owner_id, 2, source)
                # TODO: decrement_life or apply_damage?
    return E()


def feint_on_cast():
    """Tap all creatures blocking target attacking creature.
    Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = the attacker"""
            the_combat = [com for com in gs.combats if com.attacker == target]
            if not the_combat:
                return
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
            for b in the_combat[0].blockers:
                gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
                b.tap(gs)
    return E()


def flash_flood_on_cast():
    """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
            gs.return_to_hand_from_board(t) if t.props.slug == 'mountain' else gs.send_to_graveyard_from_play(t)
    return E()


def forest_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for c in gs.card_filter.on_player_board(source.orig_owner_id).result():
                if c.props.slug == 'kird-ape' and PTModifier(c, 1, 2) not in c.modifiers.auras:
                    c.modifiers.auras.append(PTModifier(c, 1, 2))
    return E()


def goblin_king_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """All of your other Goblins gain +1+/+1 and Mountainwalk"""
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Goblin').result()
            for t in targets:
                if source != t:
                    t.modifiers.auras.append(KWAModifier(source, 'add', 'Mountainwalk'))
                    t.modifiers.auras.append(PTModifier(source, 1, 1))
    return E()


def glyph_of_destruction_on_cast():
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            t.modifiers.temps(PTTemp(10, 0))
            gs.global_effects.append((s, all_damage_prevented_to_target_card(s), True))
            gs.end_step_funcs.append(lambda gs, s, t: gs.send_to_graveyard_from_play(s))
    return E()


def kobold_drill_sergeant_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """Other Kobold creatures you control get +0/+1 and have trample"""
            kobolds = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
            for k in kobolds:
                if source != k:
                    k.modifiers.auras.append(KWAModifier(source, 'add', 'Trample'))
                    k.modifiers.auras.append(PTModifier(source, 0, 1))
    return E()


def lord_of_atlantis_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """All of your other Merfolk gain +1/+1 and Islandwalk"""
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Merfolk').result()
            for t in targets:
                if source != t:
                    t.modifiers.auras.append(KWAModifier(source, 'add', 'Islandwalk'))
                    t.modifiers.auras.append(PTModifier(source, 1, 1))
    return E()


def martyrs_cry_on_cast():
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for white_creature in gs.card_filter.in_play().white().creatures().result():
                owner_id = white_creature.orig_owner_id
                gs.send_to_exile_from_play(white_creature)  # which is correct?  exile_from_play() or exile()
                gs.draw(gs.hands[owner_id], gs.decks[owner_id].cards, 1)
    return E()


def reverse_damage_on_cast():
    """The next time a source of your choice would deal damage to you this turn, prevent that damage.
    You gain life equal to the damage prevented this way.
    Since amount prevented isn't known upon cast, use PreventNextDamage.on_prevent() callback to later call gain_life"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = the GameCard doing the damage"""
            def gain_life(prevented: int):
                gs.increment_life(s.orig_owner_id, prevented)

            gs.damage_preventions.append(
                PreventNextDamage(s, None, target_player=s.orig_owner_id, source_card=target, on_prevent=gain_life))
    return E()


def rocket_launcher_on_cast():
    """To support '{2}: Activate only if card it's been in play the entire turn...'"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            s.has_summoning_sickness = True
    return E()


def sacrifice_on_cast():
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
            if not t:
                raise ValueError(f"{s.props.name} needs a target to ... sacrifice")
            gs.action_stack.push(SacCreatureAndAddMana(s.orig_owner_id, gs, s, t, 'B', t.props.casting_weight), gs, False)
    return E()


def shapeshifter_on_cast():
    """As this creature enters, choose a number (n) between 0 and 7. Power = n, Toughness = 7-n ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            gs.action_stack.push(ShapeshifterChoice(source.orig_owner_id, gs, source), gs, False)
    return E()


def subdue_on_cast():
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            gs.damage_preventions.append(PreventNextDamage(s, None, source_card=t, combat_only=True))
            t.modifiers.temps.append(PTModifier(s, 0, t.props.casting_weight))
    return E()


def syphon_soul_on_cast():
    """Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
            gs.apply_damage(source, 2, flip(source.orig_owner_id))
            gs.increment_life(source.orig_owner_id, 2)
    return E()


def web_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 0, 2))
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Reach'))
    return E()


def venarian_gold_on_cast():
    """When this Aura enters, tap enchanted creature and put X sleep counters on it ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if not target:
                raise RuntimeError(f"{source.props.name} needs a casting target")
            gs.apply_tap_effects(target)
            if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
                source.counters.add_counter(SLEEP, x)
    return E()


def swords_to_plowshares_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                gs.send_to_exile(target)  # which is correct?  exile_from_play() or exile()
                gs.increment_life(target.orig_owner_id, target.power)
    return E()


def farmstead_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(source)
    return E()
