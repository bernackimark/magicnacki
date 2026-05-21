from __future__ import annotations
import random
from typing import Optional, TYPE_CHECKING

from models.effects.damage_preventions import PreventAllDamage
from models.effects.until_end_of_turn import NoAttacksAllowedEOT
from models.events_all import DiesEvent, UnblockedAttackerEvent, AttackEvent, BlockEvent, UpkeepEvent, ZoneChangeEvent
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.choice_actions_all import SerendibDjinnUpkeepChoice, ShapeshifterChoice, \
    PayOneColorlessForOneLifeChoice, PayManaToDrawCardsChoice, FastingChoice, DrawCardsOrDontChoice, \
    RemoveCounterForLifeChoice, FloralSpuzzemChoice, HealingSalveChoice, PayManaOrTakeDamage, CycloneChoice, \
    YawgmothDemonChoice, PayLifeOrDiscardChoice, RogahhOfKherKeepUpkeepChoice
from models.actions.special import SacCreatureAndAddMana, RogahhOfKherKeepTapAndStealAction
from models.counter_tokens import PUPA, PLUS_ONE, SLEEP, HUNGER, VITALITY, WIND
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.modifiers import KWAMod, PTMod

# --- GENERICS ---
class CreateTokenCreature(Effect):
    """Looks-up token slug in GameState's 'tokens' dict; creates GameCard with .is_token = True; adds to board"""
    def __init__(self, slug: str):
        self.slug = slug

    def resolve(self, gs: GameState, source: GameCard, target=None):
        from models.game_card.game_card import GameCard
        from models.zone import Zone
        card = gs.tokens.get(self.slug)
        if not card:
            raise ValueError(f'No token found for {self.slug}')
        game_card = GameCard(card, source.owner_id, is_token=True)
        game_card.zone = Zone.BATTLEFIELD
        game_card.game_state = gs
        gs.boards[source.owner_id].append(game_card)

class RemoveHostAuras(Effect):
    """Removes target's existing auras"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        for aura in list(target.auras):
            gs.event_mgr.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'), self)
            gs.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
            gs.event_mgr.unregister_effects(aura)

# --- CARD-SPECIFIC ---
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

class Amnesia(Effect):
    """Target player reveals their hand and discards all nonland cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for c in gs.hands[target].cards[:]:
            c.reveal()
            if 'Land' not in c.card_types:
                gs.discard(c, source)

class AnimateDead(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.reanimate(target)
        target.modifiers.items.append(PTMod(s=source, p_adj=-1, t_adj=0))

class BookOfRass(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, 2, source.owner_id)
        gs.draw(source.owner_id)

class BottleOfSuleiman(Effect):
    """{1}, Sac: Flip a coin. If you win the flip, create a 5/5 colorless Djinn artifact creature token with flying.
    If you lose the flip, this artifact deals 5 damage to you."""
    def resolve(self, gs: GameState, s: GameCard, _: GameCard = None):
        result: str = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        if result == 'heads':
            obj = CreateTokenCreature('djinn')
            obj.resolve(gs, s)
            # gs.create_token_creature(s.owner_id, 'Djinn', 5, 5, ['Flying', 'Attack'],
            #                          other_types=[], sub_types=['Djinn'], colors='C')
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
        p_id = gs.turn_mgr.player_turn_idx
        host = source.host
        if p_id != source.owner_id:
            return
        if not host.counters.get_count(PUPA):
            gs.destroy(source)
            host.counters.add_counter(PLUS_ONE)
            host.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Flying'))
            return
        host.counters.remove_counter(PUPA)

class Crumble(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.destroy(target, allow_regeneration=False)
            gs.score_mgr.increment_life(target.owner_id, target.props.mana_value, source, gs)

class Cyclone(Effect):
    """At your upkeep, add a wind counter, then pay {G} for each wind counter on it or sac.
    If you pay, Cyclone deals damage = its wind counters to each creature and each player."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(WIND)
        if not gs.mana_pools[source.owner_id].can_pay('G' * source.counters.get_count(WIND)):
            gs.destroy(source, False)
        gs.action_stack.push(CycloneChoice(source.owner_id, gs, source), gs, False)

class DivineOffering(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target")
        gs.destroy(target)
        gs.score_mgr.increment_life(source.owner_id, target.props.mana_value, source, gs)

class Earthbind(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa='Flying'))
        if 'Flying' in target.keyword_abilities:
            gs.apply_damage(source, 2, target.owner_id)

class ElectricEel(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.items.append(PTMod(s=source, p_adj=2, expires='EOT'))
        gs.apply_damage(source, 1, source.owner_id)

class ElvesOfTheDeepShadow(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.mana_pools[source.owner_id].add_floating('B')
        gs.apply_damage(source, 1, source.owner_id)

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
        if gs.turn_mgr.player_turn_idx != source.owner_id:
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
        gy = gs.graveyards[s.owner_id]
        lib = gs.libraries[s.owner_id]
        lib.extend(gy)
        gy.clear()
        random.shuffle(lib)

class Festival(Effect):
    """... Creatures can't attack this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((NoAttacksAllowedEOT(), source))

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

class GoblinKing(Effect):
    """All of your other Goblins gain +1+/+1 and Mountainwalk"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        targets = gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Goblin').result()
        for t in targets:
            if source != t:
                t.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Mountainwalk'))
                t.modifiers.items.append(PTMod(s=source, p_adj=1, t_adj=1))

class Greed(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, source.owner_id)
        gs.draw(source.owner_id)

class GlyphOfDestruction(Effect):
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.items.append(PTMod(s=s, p_adj=10, expires='EOT'))
        gs.damage_preventions.append(PreventAllDamage())  # Will this prevent all damage to everyone?
        gs.end_step_funcs.append(lambda gs_, s_, t_: gs.destroy(s))

class HasranOgress(Effect):
    """Whenever this creature attacks, it deals 3 damage to you unless you pay {2}"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        gs.action_stack.push(PayManaOrTakeDamage(s.owner_id, gs, s, '2', 3), gs, False)

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

class Inquisition(Effect):
    """Target player reveals their hand. Deal damage to that player = number of white cards in their hand."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target player")
        opp_cards = gs.hands[flip(source.owner_id)].cards
        for c in opp_cards:
            c.reveal()
        if white_cnt := len([c for c in opp_cards if c.is_white]):
            gs.apply_damage(source, white_cnt, flip(source.owner_id))

class KoboldDrillSergeant(Effect):
    """Other Kobold creatures you control get +0/+1 and have trample"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        kobolds = gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result()
        for k in kobolds:
            if source != k:
                k.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Trample'))
                k.modifiers.items.append(PTMod(s=source, p_adj=0, t_adj=1))

class KryShield(Effect):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, source_card=t))
        t.modifiers.items.append(PTMod(s=s, t_adj=t.props.mana_value, expires='EOT'))

class LivingArtifactUpkeep(Effect):
    """... At your upkeep, you may remove a vitality counter from this Aura to gain 1 life"""
    def resolve(self, gs: GameState, s: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
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
            gs.exile(white_creature)
            gs.draw(white_creature.owner_id)

class MazeOfIth(Effect):
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        the_combat = next((com for com in gs.combats if com.attacker is t), None)
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
            gs.score_mgr.increment_life(s.owner_id, prevented, s, gs)

        gs.damage_preventions.append(
            PreventNextDamage(s, None, target_player=s.owner_id, source_card=target, on_prevent=gain_life))

class RocketLauncherCast(Effect):
    """To support 'Activate only if you've controlled continuously since the beginning of your most recent turn."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        s.has_summoning_sickness = True

class RocketLauncherAA(Effect):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.apply_damage(s, 1, t)
        gs.end_step_funcs.append(lambda gs_, s_: gs.destroy(s))

class RogahhOfKherKeepUpkeep(Effect):
    """... At your upkeep, pay {RRR} or else ..."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id or source.props.slug != 'rogahh-of-kher-keep':
            return
        owner = source.owner_id
        target_cards = [source] + gs.card_filter.on_player_board(owner).by_slug('kobolds-of-kher-keep').result()
        if gs.mana_pools[source.owner_id].can_pay('RRR'):
            gs.action_stack.push(RogahhOfKherKeepUpkeepChoice(source.owner_id, gs, source, target_cards), gs, False)
        else:
            action = RogahhOfKherKeepTapAndStealAction(source.owner_id, gs, source, targets=target_cards)
            action.play()

class SacrificeOnCast(Effect):
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value.
    Note "sacrifice" refers to the card called sacrifice, not the game action of sacrifice"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f"{s.props.name} needs a target to ... sacrifice")
        gs.action_stack.push(SacCreatureAndAddMana(s.owner_id, gs, s, t, 'B', t.props.mana_value), gs, False)

class SerendibDjinn(Effect):
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.action_stack.push(SerendibDjinnUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)

class Shapeshifter(Effect):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.action_stack.push(ShapeshifterChoice(source.owner_id, gs, source), gs, False)

class StoneGiant(Effect):
    """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
    Destroy that creature at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.items.append(KWAMod(s=s, add_or_remove='add', kwa='Flying', expires='EOT'))
        gs.end_step_funcs.append(lambda gs_, s_: gs.destroy(t))

class SoulNet(Effect):
    """Whenever a creature dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or not event.card.is_creature:
            return

        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)

class Subdue(Effect):
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, None, source_card=t, combat_only=True))
        t.modifiers.items.append(PTMod(s=s, p_adj=0, t_adj=t.props.mana_value))

class SwordsToPlowshares(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.exile(target)  # which is correct?  exile_from_play() or exile()
            gs.score_mgr.increment_life(target.owner_id, target.power, source, gs)

class SylvanLibrary(Effect):
    """At your draw step, you may draw two additional cards.
    If you do, choose two cards in your hand drawn this turn.
    For each of those cards, pay 4 life or put the card on top of your library."""
    # TODO: Once player opts to draw, control needs to be returned back to player to then make subsequent choices.
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.action_stack.push(DrawCardsOrDontChoice(gs.turn_mgr.player_turn_idx, gs, source, 2))

class SyphonSoul(Effect):
    """Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, target)
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)

class TabletOfEpityr(Effect):
    """Whenever an artifact you control dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)

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
            gs.libraries[p_id].extend(hand_cards)
            gs.libraries[p_id].extend(graveyard_cards)
            random.shuffle(gs.libraries[p_id])
            gs.draw(p_id, 7)
            if p_id == s.owner_id:
                gs.graveyards[p_id].append(time_twister)

class UrzasAvengerFlying(Effect):
    """This creature gets -1/-1 and gains your choice of FLYING, first strike, or trample until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.items.append(PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT'))
        source.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Flying', expires='EOT'))

class UrzasAvengerFirstStrike(Effect):
    """This creature gets -1/-1 and gains your choice of flying, FIRST STRIKE, or trample until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.items.append(PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT'))
        source.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT'))

class UrzasAvengerTrample(Effect):
    """This creature gets -1/-1 and gains your choice of flying, first strike, or TRAMPLE until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.items.append(PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT'))
        source.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Trample', expires='EOT'))

class UrzasMiter(Effect):
    """Whenever an artifact you control dies, if it wasn't sacrificed [not handling this part], {3}: draw a card"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayManaToDrawCardsChoice(source.owner_id, gs, source), gs, False)

class VenarianGoldCast(Effect):
    """When this Aura enters, tap enchanted creature and put X sleep counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a casting target")
        gs.tap_card(target)
        if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
            source.counters.add_counter(SLEEP, x)

class WallOfWonder(Effect):
    """{2UU}: This creature gets +4/-4 until end of turn and can attack this turn as though it didn't have defender"""
    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
        source.modifiers.items.append(PTMod(s=source, p_adj=4, t_adj=-4, expires='EOT'))
        source.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa='Defender', expires='EOT'))

class WandOfIth(Effect):
    """Opponent reveals a card at random from their hand. If it's a land, that player pays 1 lift or discards.
    If a non-land, the player pays life = to its mana value else discards it.  Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        opp = flip(source.owner_id)
        opp_cards = gs.hands[opp].cards
        if not opp_cards:
            return
        the_card = gs.randomize_event(opp, opp_cards) if len(opp_cards) > 1 else opp_cards[0]
        life_payment_amt = the_card.props.mana_value if 'Land' not in the_card.card_types else 1
        gs.pending_choice = PayLifeOrDiscardChoice(opp, gs, source, life_payment_amt, the_card)

class Web(Effect):
    def resolve(self, _: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.items.append(PTMod(s=source, p_adj=0, t_adj=2))
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Reach'))

class WindsOfChange(Effect):
    """Each player shuffles the cards from their hand into their library, then draws that many cards"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        for p_id in range(2):
            if not gs.hands[p_id].cards:
                continue
            hand_cards = gs.hands[p_id][:]
            gs.hands[p_id].cards.clear()
            gs.libraries[p_id].extend(hand_cards)
            random.shuffle(gs.libraries[p_id])
            gs.draw(p_id, len(hand_cards))

class WinterBlast(Effect):
    """Tap X target creatures. Winter Blast deals 2 damage to each of those creatures with flying."""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            gs.tap_card(t)
            if 'Flying' in t.keyword_abilities:
                gs.apply_damage(source, 2, t)

class WormwoodTreefolkForestwalk(Effect):
    """{GG}: This creature gains forestwalk until end of turn and deals 2 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Forestwalk', expires='EOT'))
        gs.apply_damage(source, 2, source.owner_id)

class WormwoodTreefolkSwampwalk(Effect):
    """{BB}: This creature gains swampwalk until end of turn and deals 2 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Swampwalk', expires='EOT'))
        gs.apply_damage(source, 2, source.owner_id)

class YawgmothDemon(Effect):
    """At your upkeep, Sac an artifact, or tap this creature and it deals 2 damage to you"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if source.owner_id != gs.turn_mgr.player_turn_idx:
            return
        if not gs.card_filter.on_player_board(source.owner_id).artifacts().result():
            gs.tap_card(source)
            gs.apply_damage(source, 2, source.owner_id)
            return
        gs.action_stack.push(YawgmothDemonChoice(source.owner_id, gs, source), gs, False)


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
