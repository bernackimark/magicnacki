from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from models.effects.damage_preventions import DamagePreventionEffect, PreventAllDamage
from models.events.events_all import DiesEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.choice_actions.choice_actions_all import SerendibDjinnUpkeepChoice, ShapeshifterChoice, \
    PayOneColorlessForOneLifeChoice, PayManaToDrawCardsChoice
from models.actions.special import SacCreatureAndAddMana, PayManaToDrawCards
from models.counter_tokens import PUPA, PLUS_ONE, SLEEP
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.modifiers import KWAModifier, PTModifier, PTTemp, KWATemp


class ActiveVolcano(Effect):
    """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.return_to_hand_from_board(t) if t.props.slug == 'island' else gs.send_to_graveyard_from_play(t)

class AnimateDead(Effect):
    def resolve(self, gs, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        card = gs.remove_from_your_graveyard(target, source.orig_owner_id)
        gs.boards[source.orig_owner_id].play_to_board(card)
        target.modifiers.auras.append(PTModifier(source, -1, 0))

class BookOfRass(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, 2, source.orig_owner_id)
        gs.draw(gs.hands[source.orig_owner_id], gs.decks[source.orig_owner_id].cards, 1)

class CocoonUpkeep(Effect):
    """At your upkeep, remove a pupa counter from this Aura.
        If you can't, sac it, put a +1/+1 counter on enchanted creature, and that creature gains flying."""
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

class Crumble(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.send_to_graveyard_from_play(target)
            gs.increment_life(target.orig_owner_id, target.props.casting_weight)

class DivineOffering(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError("Divine Offering needs a target")
        if target:
            gs.increment_life(source.orig_owner_id, target.power)
            gs.send_to_graveyard_from_play(target)

class Earthbind(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Flying'))
        if 'Flying' in target.keyword_abilities:
            gs.apply_damage(source, 2, target.orig_owner_id)

class ElectricEel(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.temps.append(PTTemp(source, 2, 0))
        gs.apply_damage(source, 1, source.orig_owner_id)

class ElvesOfTheDeepShadow(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.mana_pools[source.orig_owner_id].add_floating('B')
        gs.apply_damage(source, 1, source.orig_owner_id)

class Feint(Effect):
    """Tap all creatures blocking target attacking creature.
        Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the attacker"""
        the_combat = [com for com in gs.combats if com.attacker == target]
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
        for b in the_combat[0].blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
            b.tap(gs)

class FlashFlood(Effect):
    """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.return_to_hand_from_board(t) if t.props.slug == 'mountain' else gs.send_to_graveyard_from_play(t)

class ForestCast(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for c in gs.card_filter.on_player_board(source.orig_owner_id).result():
            if c.props.slug == 'kird-ape' and PTModifier(c, 1, 2) not in c.modifiers.auras:
                c.modifiers.auras.append(PTModifier(c, 1, 2))

class GoblinKing(Effect):
    """All of your other Goblins gain +1+/+1 and Mountainwalk"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Goblin').result()
        for t in targets:
            if source != t:
                t.modifiers.auras.append(KWAModifier(source, 'add', 'Mountainwalk'))
                t.modifiers.auras.append(PTModifier(source, 1, 1))

class Greed(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, source.orig_owner_id)
        gs.draw(gs.hands[source.orig_owner_id], gs.decks[source.orig_owner_id].cards, 1)

class GlyphOfDestruction(Effect):
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.temps(PTTemp(s, 10, 0))
        gs.damage_preventions.append(PreventAllDamage())  # Will this prevent all damage to everyone?
        gs.end_step_funcs.append(lambda gs, s, t: gs.send_to_graveyard_from_play(s))

class KoboldDrillSergeant(Effect):
    """Other Kobold creatures you control get +0/+1 and have trample"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        kobolds = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
        for k in kobolds:
            if source != k:
                k.modifiers.auras.append(KWAModifier(source, 'add', 'Trample'))
                k.modifiers.auras.append(PTModifier(source, 0, 1))

class KryShield(Effect):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, source_card=t))
        t.modifiers.temps.append(PTTemp(s, 0, t.props.casting_weight))

class MartyrsCry(Effect):
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for white_creature in gs.card_filter.in_play().white().creatures().result():
            owner_id = white_creature.orig_owner_id
            gs.send_to_exile_from_play(white_creature)  # which is correct?  exile_from_play() or exile()
            gs.draw(gs.hands[owner_id], gs.decks[owner_id].cards, 1)

class MazeOfIth(Effect):
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        the_combat = next((com for com in gs.combats if com.attacker == t), None)
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, combat_only=True))
        for b in the_combat.blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
        t.untap(gs)

class Rakalite(Effect):
    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if not target:
            raise RuntimeError(f'{s.props.name} needs a target')
        prevention = PreventNextDamage(s, None, source_card=target)
        gs.damage_preventions.append(prevention)
        gs.return_to_hand_from_board(s)

class ReverseDamage(Effect):
    """The next time a source of your choice would deal damage to you this turn, prevent that damage.
    You gain life equal to the damage prevented this way.
    Since amount prevented isn't known upon cast, use PreventNextDamage.on_prevent() callback to later call gain_life"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the GameCard doing the damage"""
        def gain_life(prevented: int):
            gs.increment_life(s.orig_owner_id, prevented)

        gs.damage_preventions.append(
            PreventNextDamage(s, None, target_player=s.orig_owner_id, source_card=target, on_prevent=gain_life))

class RocketLauncherCast(Effect):
    """To support 'Activate only if you've controlled continuously since the beginning of your most recent turn."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        s.has_summoning_sickness = True

class RocketLauncherAA(Effect):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.apply_damage(s, 1, t)
        gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(s))

class SacrificeOnCast(Effect):
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value.
    Note "sacrifice" refers to the card called sacrifice, not the game action of sacrifice"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f"{s.props.name} needs a target to ... sacrifice")
        gs.action_stack.push(SacCreatureAndAddMana(s.orig_owner_id, gs, s, t, 'B', t.props.casting_weight), gs, False)

class SerendibDjinn(Effect):
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.player_turn_idx != source.orig_owner_id:
            return
        gs.action_stack.push(SerendibDjinnUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)

class Shapeshifter(Effect):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != source.orig_owner_id:
            return
        gs.action_stack.push(ShapeshifterChoice(source.orig_owner_id, gs, source), gs, False)

class StoneGiant(Effect):
    """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
    Destroy that creature at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.temps.append(KWATemp(s, 'add', 'Flying'))
        gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(t))

class SoulNet(Effect):
    """Whenever a creature dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent):
            return

        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.orig_owner_id, gs, source), gs, False)

class Subdue(Effect):
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, None, source_card=t, combat_only=True))
        t.modifiers.temps.append(PTModifier(s, 0, t.props.casting_weight))

class SwordsToPlowshares(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.send_to_exile_from_play(target)  # which is correct?  exile_from_play() or exile()
            gs.increment_life(target.orig_owner_id, target.power)

class SyphonSoul(Effect):
    """Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, target)
        gs.increment_life(source.orig_owner_id, 2)

class TabletOfEpityr(Effect):
    """Whenever an artifact you control dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.orig_owner_id != source.orig_owner_id:
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.orig_owner_id, gs, source), gs, False)

class UrzasMiter(Effect):
    """ Whenever an artifact you control dies, if it wasn't sacrificed [not handling this part], {3}: draw a card"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.orig_owner_id != source.orig_owner_id:
            return
        gs.action_stack.push(PayManaToDrawCardsChoice(source.orig_owner_id, gs, source), gs, False)

class VenarianGoldCast(Effect):
    """When this Aura enters, tap enchanted creature and put X sleep counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a casting target")
        gs.tap_card(target)
        if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
            source.counters.add_counter(SLEEP, x)
class Web(Effect):
    def resolve(self, _: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.auras.append(PTModifier(source, 0, 2))
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Reach'))
