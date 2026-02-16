from __future__ import annotations
import random
from typing import Optional, TYPE_CHECKING

from models.effects.damage_preventions import PreventAllDamage
from models.events_all import DiesEvent, UnblockedAttackerEvent, AttackEvent, BlockEvent
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.choice_actions_all import SerendibDjinnUpkeepChoice, ShapeshifterChoice, \
    PayOneColorlessForOneLifeChoice, PayManaToDrawCardsChoice, FastingChoice, DrawCardsOrDontChoice, \
    RemoveCounterForLifeChoice, FloralSpuzzemChoice, HealingSalveChoice
from models.actions.special import SacCreatureAndAddMana
from models.counter_tokens import PUPA, PLUS_ONE, SLEEP, HUNGER, VITALITY
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.modifiers import KWAModifier, PTModifier, PTTemp, KWATemp


class CreateTokenCreature(Effect):
    """Generic to create a GameCard with .is_token = True and place it on the board"""
    def __init__(self, name: str, power: int, toughness: int, kwa: list[str],
                 other_types: list[str], sub_types: list[str], colors: str):
        self.name = name
        self.power = power
        self.toughness = toughness
        self.kwa = kwa
        self.other_types = other_types
        self.sub_types = sub_types or []
        self.colors = colors or ''

    def resolve(self, gs: GameState, source: GameCard, target=None):
        gs.create_token_creature(owner_id=source.owner_id, name=self.name, power=self.power, toughness=self.toughness,
                                 kwa=self.kwa, other_types=self.other_types, sub_types=self.sub_types,
                                 colors=self.colors)

class AshnodsTransmogrant(Effect):
    """{T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature.
    That creature becomes an artifact in addition to its other types."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise RuntimeError(f'{s.props.name} needs a target')
        t.counters.add_counter(PLUS_ONE)
        t.card_types.append('Artifact')

class ActiveVolcano(Effect):
    """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.bounce(t) if t.props.slug == 'island' else gs.destroy(t)

class AnimateDead(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.reanimate(target)
        target.modifiers.auras.append(PTModifier(source, -1, 0))

class BookOfRass(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, 2, source.orig_owner_id)
        gs.draw(source.owner_id)

class BottleOfSuleiman(Effect):
    """{1}, Sac: Flip a coin. If you win the flip, create a 5/5 colorless Djinn artifact creature token with flying.
    If you lose the flip, this artifact deals 5 damage to you."""
    def resolve(self, gs: GameState, s: GameCard, _: GameCard = None):
        result: str = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        if result == 'heads':
            gs.create_token_creature(s.owner_id, 'Djinn', 5, 5, ['Flying', 'Attack'],
                                     other_types=[], sub_types=['Djinn'], colors='C')
        else:
            gs.apply_damage(s, 5, s.owner_id)

class ChaosOrb(Effect):
    """{1}, {T}, Sac: Choose an opponent's non-token permanent. If random di roll is 1-4, destroy target."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        result: int = gs.randomize_event(s.owner_id, [1, 2, 3, 4, 5, 6])
        if result <= 4:
            gs.destroy(t)

class CocoonUpkeep(Effect):
    """At your upkeep, remove a pupa counter from this Aura.
        If you can't, sac it, put a +1/+1 counter on enchanted creature, and that creature gains flying."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = gs.player_turn_idx
        host = source.attached_to
        if p_id != source.orig_owner_id:
            return
        if not host.counters.get_count(PUPA):
            gs.destroy(source)
            host.counters.add_counter(PLUS_ONE)
            host.modifiers.auras.append(KWAModifier(source, 'add', 'Flying'))
            return
        host.counters.remove_counter(PUPA)

class Crumble(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.destroy(target)
            gs.increment_life(target.orig_owner_id, target.props.casting_weight)

class DivineOffering(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target")
        if target:
            gs.increment_life(source.orig_owner_id, target.power)
            gs.destroy(target)

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

class FallingStar(Effect):
    """Select an opponent's creature. If a di roll is 1-5, deal 3 damage to it"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        result: int = gs.randomize_event(s.owner_id, [1, 2, 3, 4, 5, 6])
        print(f'The roll is a: {result}')
        if result <= 5:
            gs.apply_damage(s, 3, t)

class Fasting(Effect):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.player_turn_idx != source.orig_owner_id:
            return
        source.counters.add_counter(HUNGER)
        if source.counters.get_count(HUNGER) > 4:
            gs.destroy(source)
        gs.action_stack.push(FastingChoice(source.owner_id, gs, source), gs, False)


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

class FeldonsCane(Effect):
    """{T}, Exile this artifact: Shuffle your graveyard into your library."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        graveyard_cards = gs.graveyards[s.owner_id][:]
        gs.graveyards.clear()
        gs.libraries[s.owner_id].cards.extend(graveyard_cards)
        random.shuffle(gs.libraries[s.owner_id].cards)

class FlashFlood(Effect):
    """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.bounce(t) if t.props.slug == 'mountain' else gs.destroy(t)

class FloralSpuzzem(Effect):
    """Whenever this creature walks, you may destroy target opp artifact instead of dealing the combat damage."""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s or not gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result():
            return
        gs.action_stack.push(FloralSpuzzemChoice(s.owner_id, gs, s), gs, False)

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
        gs.draw(source.owner_id)

class GlyphOfDestruction(Effect):
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.temps(PTTemp(s, 10, 0))
        gs.damage_preventions.append(PreventAllDamage())  # Will this prevent all damage to everyone?
        gs.end_step_funcs.append(lambda gs, s, t: gs.destroy(s))

class HealingSalve(Effect):
    """Choose one - * You gain 3 life. * Prevent the next 3 damage that would be dealt to any target this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pending_choice = HealingSalveChoice(s.owner_id, gs, s)

class HurkylsRecall(Effect):
    """Return all artifacts target player owns to their hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target player")
        for artifact in gs.card_filter.on_player_board(target).artifacts().result():
            gs.bounce(artifact)

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

class LivingArtifactUpkeep(Effect):
    """... At your upkeep, you may remove a vitality counter from this Aura to gain 1 life"""
    def resolve(self, gs: GameState, s: GameCard, target=None):
        if gs.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(RemoveCounterForLifeChoice(s.owner_id, gs, s, VITALITY), gs, False)

class ManaClash(Effect):
    """You and target opponent each flip a coin. Mana Clash deals 1 damage to each player whose coin comes up tails.
    Repeat this process until both players' coins come up heads on the same flip."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        caster_id, opp_id = source.owner_id, flip(source.owner_id)
        while True:
            caster_result = gs.randomize_event(caster_id, ['heads', 'tails'])
            opp_result = gs.randomize_event(opp_id, ['heads', 'tails'])
            print(f"Caster's result is {caster_result}; opponent's result is {opp_result}")
            if caster_result == 'heads' and opp_result == 'heads':
                print('Since both flips were heads, there are no more flips')
                break
            if caster_result == 'tails':
                gs.apply_damage(source, 1, caster_id)
            if opp_result == 'tails':
                gs.apply_damage(source, 1, opp_id)

class MartyrsCry(Effect):
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for white_creature in gs.card_filter.in_play().white().creatures().result():
            gs.exile(white_creature)  # which is correct?  exile_from_play() or exile()
            gs.draw(white_creature.owner_id)

class MazeOfIth(Effect):
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        the_combat = next((com for com in gs.combats if com.attacker == t), None)
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, combat_only=True))
        for b in the_combat.blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
        t.untap(gs)

class MijaeDjinn(Effect):
    """Whenever this creature attacks, flip a coin. If you lose the flip, remove this creature from combat and tap it"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        result = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        print(f'The result of the random event was: {result}')
        if result == 'tails':
            gs.remove_from_combat(s)
            gs.tap_card(s)

class Rakalite(Effect):
    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if not target:
            raise RuntimeError(f'{s.props.name} needs a target')
        prevention = PreventNextDamage(s, None, source_card=target)
        gs.damage_preventions.append(prevention)
        gs.bounce(s)

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
        gs.end_step_funcs.append(lambda gs, s: gs.destroy(s))

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
        gs.end_step_funcs.append(lambda gs, s: gs.destroy(t))

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
            gs.exile(target)  # which is correct?  exile_from_play() or exile()
            gs.increment_life(target.orig_owner_id, target.power)

class SylvanLibrary(Effect):
    """At your draw step, you may draw two additional cards.
    If you do, choose two cards in your hand drawn this turn.
    For each of those cards, pay 4 life or put the card on top of your library."""
    # TODO: Once player opts to draw, control needs to be returned back to player to then make subsequent choices.
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.action_stack.push(DrawCardsOrDontChoice(gs.player_turn_idx, gs, source, 2))

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

class Timetwister(Effect):
    """Each player shuffles their hand & graveyard into their library, then draws 7 cards.
    (Timetwister to its owner's graveyard.)"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        time_twister = next(c for c in gs.graveyards[s.owner_id] if c is s)
        for p_id in range(2):
            hand_cards = gs.hands[p_id][:]
            gs.hands[p_id].cards.clear()
            graveyard_cards = gs.graveyards[p_id][:]
            gs.graveyards.clear()
            gs.libraries[p_id].cards.extend(hand_cards)
            gs.libraries[p_id].cards.extend(graveyard_cards)
            random.shuffle(gs.libraries[p_id].cards)
            gs.draw(p_id, 7)
            if p_id == s.owner_id:
                gs.graveyards[p_id].append(time_twister)

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

class WindsOfChange(Effect):
    """Each player shuffles the cards from their hand into their library, then draws that many cards"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        for p_id in range(2):
            if not gs.hands[p_id].cards:
                continue
            hand_cards = gs.hands[p_id][:]
            gs.hands[p_id].cards.clear()
            gs.libraries[p_id].cards.extend(hand_cards)
            random.shuffle(gs.libraries[p_id].cards)
            gs.draw(p_id, len(hand_cards))

class WormwoodTreefolkForestwalk(Effect):
    """{GG}: This creature gains forestwalk until end of turn and deals 2 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.modifiers.temps.append(KWATemp(source, 'add', 'Forestwalk'))
        gs.apply_damage(source, 2, source.orig_owner_id)

class WormwoodTreefolkSwampwalk(Effect):
    """{BB}: This creature gains swampwalk until end of turn and deals 2 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.modifiers.temps.append(KWATemp(source, 'add', 'Swampwalk'))
        gs.apply_damage(source, 2, source.orig_owner_id)

class YdwenEfreet(Effect):
    """Whenever Ydwen Efreet blocks, flip a coin.
    If you lose, remove Ydwen Efreet from combat who can't block this turn."""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.blocker is not s:
            return
        result = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        print(f'The result of the random event was: {result}')
        if result == 'tails':
            gs.remove_from_combat(s)
