from __future__ import annotations
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.destroy_sac_regen import DestroyAction, TheAbyssAction
from models.actions.draw_discard import DiscardCard
from models.actions.special import RogahhOfKherKeepTapAndStealAction
from models.actions.tap_untap import LeaveTapped
from models.choice_actions_all import PayManaOrTakeDamage, PayOneColorlessForOneLifeChoice, PayManaToDrawCardsChoice, \
    FloralSpuzzemChoice, CosmicHorrorUpkeepChoice, CurseArtifactUpkeepChoice, CycloneChoice, OpponentDestroysLandChoice, \
    DemonicHordesUpkeepChoice, ElderSpawnUpkeepChoice, PayManaOrSacUpkeepChoice, ErhnamDjinnChoice, ErosionUpkeepChoice, \
    ForceOfNatureUpkeepChoice, LandTaxChoice, LordOfThePitUpkeepChoice, SacChoice, PsychicAllergyUpkeepChoice, \
    RogahhOfKherKeepUpkeepChoice, PayLifeOrSacChoice, CopyCardChoice, YawgmothDemonChoice, MoldDemonChoice, \
    DrawCardsOrDontChoice
from models.counter_tokens import PLUS_ONE, VITALITY, PIN, MINUS_ZERO_TWO, WIND
from models.effects.base import Listener
from models.effects.listeners_generic import DestroyAtCombatEnd, AddCounterAtEndStep
from models.effects.resolvers_generic import Steal
from models.events_all import AttackEvent, BlockEvent, CombatEndEvent, DamageResolvedEvent, DiesEvent, DiscardEvent, \
    DiscardStepEvent, DrawCardEvent, DrawStepEvent, EndStepEvent, LifeLossEvent, StateBasedEvent, TapCardEvent, \
    UnblockedAttackerEvent, UntapPhaseEvent, UpkeepEvent, Event, ZoneChangeEvent
from models.modifiers import PTMod, KWAMod
from models.utils import flip
from models.zone import Zone

# --- ATTACK EVENT ---
class CavePeopleAttackPump(Listener):
    """Whenever this creature attacks, it gets +1/-2 until end of turn ..."""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker is not s:
            return
        event.attacker.modifiers.append(PTMod(s=s, p_adj=1, t_adj=-2, expires='EOT'))


class HasranOgress(Listener):
    """Whenever this creature attacks, it deals 3 damage to you unless you pay {2}"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        gs.action_stack.push(PayManaOrTakeDamage(s.owner_id, gs, s, '2', 3), gs, False)


class MijaeDjinn(Listener):
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


# --- BLOCK EVENT ---
class Abomination(Listener):
    """Whenever this creature blocks or becomes blocked by a G or W creature, destroy that creature at combat end"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker == s:
            other = event.blocker
        elif event.blocker == s:
            other = event.attacker
        else:
            return
        if not any(c in other.colors for c in ('G', 'W')):
            return
        delayed = DestroyAtCombatEnd(s, other)
        gs.event_mgr.register_effect(delayed, s)
        # this will later get unregistered at combat end


class CockatriceAndThicketBasilisk(Listener):
    """Whenever this creature blocks / becomes blocked by a non-Wall creature, destroy that creature at end of combat"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker == s:
            other = event.blocker
        elif event.blocker == s:
            other = event.attacker
        else:
            return
        if 'Wall' in other.card_sub_types:
            return
        delayed = DestroyAtCombatEnd(s, other)
        gs.event_mgr.register_effect(delayed, s)
        # this will later get unregistered at combat end


class ElderLandWurm(Listener):
    """When this creature blocks for the first time, it loses defender"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.blocker is not s:
            return
        s.modifiers.append(KWAMod(s=s, add_or_remove='remove', kwa='Defender'))


class GiantShark(Listener):
    """Whenever this creature blocks/is blocked by a creature that's been dealt damage this turn,
    this creature gets +2/+0 and gains trample until end of turn"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker == s:
            other = event.blocker
        elif event.blocker == s:
            other = event.attacker
        else:
            return
        if other.damage_received_this_turn:
            s.modifiers.append(PTMod(s=s, p_adj=2, expires='EOT'))
            s.modifiers.append(KWAMod(s=s, add_or_remove='add', kwa='Trample', expires='EOT'))


class GlyphOfDoomListener(Listener):
    """Registered by GlyphOfDoom. At this turn's combat end, destroy creature blocked by that wall this turn."""
    listens_to = BlockEvent

    def __init__(self, the_wall: GameCard):
        self.the_wall = the_wall

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.blocker is not self.the_wall:
            return
        delayed = DestroyAtCombatEnd(self.the_wall, event.attacker)
        gs.event_mgr.register_effect(delayed, self.the_wall)
        # this will later get unregistered at combat end


class InfernalMedusa(Listener):
    """Whenever this creature blocks, destroy attacker at combat end.
    Whenever this creature becomes blocked by a non-Wall creature, destroy blocker at combat end."""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker is s and 'Wall' not in event.blocker.card_sub_types:
            other = event.blocker
        elif event.blocker is s:
            other = event.attacker
        else:
            return
        delayed = DestroyAtCombatEnd(s, other)
        gs.event_mgr.register_effect(delayed, s)
        # this will later get unregistered at combat end


class InfiniteAuthority(Listener):
    """Whenever host blocks/is blocked by a creature with toughness <= 3, destroy the other creature at end of combat.
    At end step, if that creature was destroyed this way, put a +1/+1 counter on host"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if s.host is event.attacker:
            other = event.blocker
        elif s.host is event.blocker:
            other = event.attacker
        else:
            return
        if other.toughness > 3:
            return
        delayed_destroy = DestroyAtCombatEnd(s, other)
        gs.event_mgr.register_effect(delayed_destroy, s)
        # this will later get unregistered at combat end

        delayed_pump = AddCounterAtEndStep(s, s.host, PLUS_ONE)
        gs.event_mgr.register_effect(delayed_pump, s)
        # this will later get unregistered at end step


class Sentinel(Listener):
    """Indefinitely change Sentinel's base T to 1 + power of target creature blocking or blocked by this creature"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker is s:
            other = event.blocker
        elif event.blocker is s:
            other = event.attacker
        else:
            return
        new_t = other.power + 1
        s.modifiers.append(PTMod(s=s, p_adj=0, t_adj=new_t - s.toughness))


class Venom(Listener):
    """Whenever host blocks / becomes blocked by a non-Wall creature, destroy that creature at end of combat"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker is s.host:
            other = event.blocker
        elif event.blocker is s.host:
            other = event.attacker
        else:
            return
        if 'Wall' in other.card_sub_types:
            return
        delayed = DestroyAtCombatEnd(s, other)
        gs.event_mgr.register_effect(delayed, s)
        # this will later get unregistered at combat end


class AislingLeprechaun(Listener):
    """Whenever this creature blocks or becomes blocked, that creature becomes green indefinitely;
    from Google: causes the creature to become green, which removes its existing colors & replaces with green only"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker == s:
            other = event.blocker
        elif event.blocker == s:
            other = event.attacker
        else:
            return
        other.colors = 'G'


class YdwenEfreet(Listener):
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


# --- COMBAT END ---
class TimeElementalAttackedOrBlocked(Listener):
    """When this creature attacks or blocks, at end of combat, sacrifice it & it deals 5 damage to you"""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if s not in gs.card_filter.combatants().result():
            return
        gs.apply_damage(s, 5, s.owner_id)
        gs.destroy(s)


# --- DAMAGE EVENT ---
class Backfire(Listener):
    """Whenever host deals damage to you, this Aura deals that much damage to that creature's controller"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.host and event.target == source.owner_id:
            gs.apply_damage(source, event.amt, source.host.owner_id)


class ElHajjaj(Listener):
    """Whenever this creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source and event.amt > 0:
            gs.score_mgr.increment_life(source.owner_id, event.amt, source, gs)


class FungusaurOnDamage(Listener):
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(PLUS_ONE)


class GlyphOfLifeListener(Listener):
    """Registered by GlyphOfLife. Whenever that wall is dealt damage by an attacker this turn, gain that much life."""
    listens_to = DamageResolvedEvent

    def __init__(self, the_wall: GameCard):
        self.the_wall = the_wall

    def on_event(self, gs: GameState, s: GameCard, event: DamageResolvedEvent):
        if event.target is not self.the_wall or not event.is_combat:
            return
        gs.score_mgr.increment_life(s.owner_id, event.amt, s, gs)


class HypnoticSpecter(Listener):
    """Whenever this creature deals damage to an opponent, that player discards a card at random"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp_id = flip(source.owner_id)
        if event.source is not source or event.target is not opp_id:
            return
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) == 1:
            gs.discard(opp_cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
        gs.discard(random_card, source)


class LivingArtifactOnDamage(Listener):
    """Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura ...
    You can target opponent artifacts. The controller of the Aura controls the Living Artifact ability"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(VITALITY)


class NicolBolas(Listener):
    """Whenever this creature deals damage to an opponent, that player discards their hand"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp_id = flip(source.owner_id)
        if event.source is not source or event.target is not opp_id:
            return
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        for c in opp_cards:
            gs.discard(c, source)


class SpiritLink(Listener):
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.host and event.amt > 0:
            gs.score_mgr.increment_life(source.owner_id, event.amt, source, gs)


# --- DIES EVENT ---
class AbuJafar(Listener):
    """When this creature dies, destroy all creatures blocking or blocked by it. They can't be regenerated."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if event.card is not source:
            return
        for com in gs.combats:
            for other_combatant in com.get_combatants_against(event.card):
                gs.destroy(other_combatant, allow_regeneration=False)


class CreatureBond(Listener):
    """When enchanted creature dies, deal damage = to host's toughness to the creature's controller"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source.host:
            return
        gs.apply_damage(source, source.host.toughness, source.host.owner_id)


class CyclopeanMummy(Listener):
    """When this creature dies, exile it"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.exile(source)


class Onulet(Listener):
    """When this creature dies, you gain 2 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class PersonalIncarnation(Listener):
    """... When this creature dies, its owner loses half their life, rounding up the loss amount"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        reduce_life_by = math.ceil(gs.score_mgr.life[source.owner_id] / 2)
        gs.apply_damage(source, reduce_life_by, source.owner_id)


class RukhEgg(Listener):
    """When this creature dies, create a 4/4 red Bird creature token with flying at next end step"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        from models.effects.resolvers_generic import CreateTokenCreature
        obj = CreateTokenCreature('rukh')
        obj.resolve(gs, source)
        # gs.create_token_creature(source.owner_id, 'Bird', 4, 4, ['Flying', 'Attack'], [], ['Bird'], 'R')


class SandalsOfAbdallahIfCreatureDies(Listener):
    """When that creature [that Sandals gave Islandwalk to] dies this turn, destroy this artifact"""
    listens_to = DiesEvent

    def __init__(self, target_creature: GameCard):
        self.target_creature = target_creature

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != self.target_creature:
            return
        gs.destroy(source)


class SuChi(Listener):
    """When this creature dies, add {CCCC}"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.mana_pools[source.owner_id].add_floating('C', 4)


class SoulNet(Listener):
    """Whenever a creature dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or not event.card.is_creature:
            return

        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)


class TabletOfEpityr(Listener):
    """Whenever an artifact you control dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)


class UrzasMiter(Listener):
    """Whenever an artifact you control dies, if it wasn't sacrificed [not handling this part], {3}: draw a card"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayManaToDrawCardsChoice(source.owner_id, gs, source), gs, False)


# --- DISCARD EVENT ---
class PsychicPurgeDiscard(Listener):
    """... When a spell or ability an opponent controls causes you to discard this card, that player loses 5 life"""
    listens_to = DiscardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        if not event.source or event.source.owner_id != source.owner_id:
            return
        gs.apply_damage(source, 5, event.source.owner_id)


# --- DISCARD STEP ---
class CursedRackEffect(Listener):
    """Opponent's maximum hand size is four [at their discard phase]"""
    listens_to = DiscardStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        opp_id = flip(source.owner_id)
        if gs.turn_mgr.player_turn_idx != opp_id:
            return

        hand = gs.hands[opp_id]
        for i in range(len(hand.cards) - 4):
            gs.action_stack.push(DiscardCard(opp_id, gs, hand.cards[0]), gs, False)


# --- DRAW CARD ---
class UnderworldDreams(Listener):
    """Whenever an opponent draws a card, this enchantment deals 1 damage to that player"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if source.owner_id == event.player_id:
            return
        gs.apply_damage(source, 1, event.player_id)


# --- DRAW STEP ---
class HowlingMine(Listener):
    """At each player's draw step, if this artifact is untapped, that player draws an additional card"""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent):
        if source.is_tapped:
            return
        gs.draw(event.active_player)


class ManaVaultDamageIfTapped(Listener):
    """... At your draw step, if this artifact is tapped, it deals 1 damage to you ..."""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: DrawStepEvent):
        if event.active_player != s.owner_id or not s.is_tapped:
            return
        gs.apply_damage(s, 1, s.owner_id)


# --- END STEP ---
class DragonWhelpEndStep(Listener):
    """If this [pump] ability has been activated 4+ times this turn, sac at end step."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if len([temp for temp in s.modifiers.items if temp.source is s]) >= 4:
            gs.destroy(s, allow_regeneration=False)


class ErgRaiders(Listener):
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id or s.has_summoning_sickness:
            return
        if s not in gs.card_filter.attackers().result():
            gs.apply_damage(s, 2, s.owner_id)


class PestilenceEndStep(Listener):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if not gs.card_filter.creatures().in_play().result():
            gs.destroy(source)


class SeasonOfTheWitchEndStep(Listener):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has Defender"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Defender' in creature.keyword_abilities:
                continue
            gs.destroy(creature)


class VoodooDollEndStep(Listener):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.owner_id)
        gs.destroy(source)


# --- LIFE LOSS ---
class AliFromCairo(Listener):
    """Damage that would reduce your life total to less than 1 reduces it to 1 instead"""
    listens_to = LifeLossEvent

    def on_event(self, gs: GameState, s: GameCard, event: LifeLossEvent):
        if event.p_id_taking_damage != s.owner_id:
            return

        current_life = gs.score_mgr.life[event.p_id_taking_damage]

        if current_life - event.amt < 1:
            event.amt = max(current_life - 1, 0)


# --- STATE CHANGE ---
class GoblinsOfTheFlarg(Listener):
    """When you control a Dwarf, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        if source.props.slug != 'goblins-of-the-flarg':
            return None

        if gs.card_filter.on_player_board(source.owner_id).by_sub_type('Dwarf').result():
            gs.destroy(source)


class SerendibDjinnNoLands(Listener):
    """When you control no lands, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            print(f'Player #{source.owner_id} has no lands, so Serendib Djinn is destroyed')
            gs.destroy(source)


# --- TAP EVENT ---
class Blight(Listener):
    """Enchant land; When enchanted land becomes tapped, destroy it."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if not source.host or source.props.slug != 'blight' or event.card is not source.host:
            return
        gs.destroy(source.host)


class CityOfBrassDamageOnTap(Listener):
    """Whenever this land becomes tapped, it deals 1 damage to you"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if event.card is not source:
            return
        gs.apply_damage(source, 1, source.owner_id)


class Lifeblood(Listener):
    """Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card.owner_id == s.owner_id:
            return
        if 'Mountain' in event.card.card_sub_types:
            gs.score_mgr.increment_life(s.owner_id, 1, s, gs)


class Lifetap(Listener):
    """Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card.owner_id == s.owner_id:
            return
        if 'Forest' in event.card.card_sub_types:
            gs.score_mgr.increment_life(s.owner_id, 1, s, gs)


class PsychicVenom(Listener):
    """Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.host:
            return
        gs.apply_damage(s, 2, event.card.owner_id)


class SpiritShackle(Listener):
    """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.host:
            return
        s.host.counters.add_counter(MINUS_ZERO_TWO)


class WildGrowth(Listener):
    """Enchant land Whenever enchanted land is tapped for mana, its controller adds another {G}"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if source.host is not event.card:
            return
        gs.mana_pools[event.card.owner_id].add_floating('G')


# --- UNBLOCKED ---
class FloralSpuzzem(Listener):
    """Whenever this creature walks, you may destroy target opp artifact instead of dealing the combat damage."""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s or not gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result():
            return
        gs.action_stack.push(FloralSpuzzemChoice(s.owner_id, gs, s), gs, False)


class MerchantShip(Listener):
    """Whenever this creature attacks and isn't blocked, you gain 2 life"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        gs.score_mgr.increment_life(s.owner_id, 2, s, gs)


class MurkDwellers(Listener):
    """Whenever this creature attacks and isn't blocked, it gets +2/+0 until end of combat"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        s.modifiers.append(PTMod(s=s, p_adj=2, expires='EOT'))


# --- UNTAP PHASE ---
class MagneticMountainOnUntapStep(Listener):
    """Blue creatures don't untap during their controllers' untap steps"""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, s: GameCard, event: UntapPhaseEvent):
        if event.active_player != s.owner_id:
            return
        if s in gs.card_filter.on_player_board(event.active_player).blue().creatures().result():
            gs.action_stack.push(LeaveTapped(s.owner_id, gs, s), gs, False)


# --- UPKEEP ---
class BlackVise(Listener):
    """As opponent's upkeep, this artifact deals X damage to that player, X is = cards in their hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.hands[opp_id].cards)
        if opp_hand_len > 4:
            gs.apply_damage(s, opp_hand_len - 4, opp_id)


class CosmicHorror(Listener):
    """At your upkeep, destroy unless you pay {3BBB}. If destroyed this way, it deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if not gs.mana_pools[source.owner_id].can_pay('3BBB'):
            gs.destroy(source)
            gs.apply_damage(source, 7, source.owner_id)
            return
        gs.action_stack.push(CosmicHorrorUpkeepChoice(source.owner_id, gs, source), gs, False)


class CurseArtifact(Listener):
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(CurseArtifactUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)


class Cyclone(Listener):
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


class DemonicHordesUpkeep(Listener):
    """... At your upkeep, pay {BBB} or tap this creature and sacrifice a land of an opponent's choice"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            gs.tap_card(source)
        elif len(your_lands) == 1:
            gs.tap_card(source)
            gs.destroy(your_lands[0])
        elif not gs.mana_pools[source.owner_id].can_pay('BBB'):
            gs.action_stack.push(OpponentDestroysLandChoice(flip(source.owner_id), gs, source))
        else:
            gs.action_stack.push(DemonicHordesUpkeepChoice(source.owner_id, gs, source), gs, False)


class ElderSpawnUpkeep(Listener):
    """At YOUR upkeep, sac an Island or sac this creature & it deals 6 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(ElderSpawnUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, s), gs, False)


class EnergyFlux(Listener):
    """All artifacts have 'At your [the owner's] upkeep, sacrifice this artifact unless you pay {2}'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_artifact in gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).artifacts().result():
            gs.action_stack.push(PayManaOrSacUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, your_artifact, '2'), gs, False)


class ErhnamDjinn(Listener):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = ErhnamDjinnChoice(s.owner_id, gs, s)


class ErosionUpkeep(Listener):
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(ErosionUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)


class ForceOfNatureUpkeep(Listener):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(ForceOfNatureUpkeepChoice(s.owner_id, gs, s, 'GGGG', 8), gs, False)


class GhazbanOgre(Listener):
    """At your upkeep, if a player has more life than each other player,
    the player with the most life gains control of this creature (assuming "your" = the current controller)"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: Event):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if len(set(gs.score_mgr.life)) == 1:
            return
        most_life_player_idx = max(range(len(gs.score_mgr.life)), key=lambda i: gs.score_mgr.life[i])
        if most_life_player_idx != source.owner_id:
            Steal().resolve(gs, source, source)


class IvoryTower(Listener):
    """At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = source.owner_id
        if p_id != event.active_player:
            return
        if (hand_size := len(gs.hands[p_id].cards)) > 4:
            gs.score_mgr.increment_life(p_id, hand_size - 4, source, gs)


class Karma(Listener):
    """At each player's upkeep, this enchantment deals damage to that player = number of Swamps they control."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        swamp_cnt = len(gs.card_filter.on_player_board(event.active_player).swamps().result())
        if swamp_cnt:
            gs.apply_damage(source, swamp_cnt, event.active_player)


class LandTax(Listener):
    """At your upkeep, if an opponent controls more lands than you, you may:
    search your library for up to 3 basic land cards, reveal them, put them into your hand, then shuffle"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_land_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).lands().result())
        if not opp_land_cnt > your_land_cnt:
            return
        gs.pending_choice = LandTaxChoice(source.owner_id, gs, source)


class LordOfThePitUpkeep(Listener):
    """At your upkeep, sacrifice a different creature. If you can't, this creature deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        choice_obj = LordOfThePitUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source)
        if not choice_obj.get_actions():
            gs.apply_damage(source, 7, source.owner_id)
            return
        gs.action_stack.push(choice_obj, gs, False)


class ManaVortexUpkeep(Listener):
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if len(gs.card_filter.lands().in_play().result()) == 0:
            gs.destroy(source)
            return
        your_lands = gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).lands().result()
        gs.action_stack.push(SacChoice(gs.turn_mgr.player_turn_idx, gs, source, your_lands), gs, False)


class PowerSurge(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is the number of untapped lands they controlled at the beginning of this turn"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        untapped_lands = gs.card_filter.in_play().untapped().lands().result()
        if untapped_lands:
            gs.apply_damage(source, len(untapped_lands), gs.turn_mgr.player_turn_idx)


class PsychicAllergyUpkeep(Listener):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_island_cnt = len([i for i in gs.card_filter.on_player_board(source.owner_id).islands().result()])
        if your_island_cnt < 2:
            gs.destroy(source)
            return
        possible_actions = PsychicAllergyUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source).get_actions()
        for action in possible_actions:
            gs.action_stack.push(action, gs, False)


class RogahhOfKherKeepUpkeep(Listener):
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


class SeasonOfTheWitchUpkeep(Listener):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        gs.action_stack.push(PayLifeOrSacChoice(source.owner_id, gs, source, 2), gs, False)


class SpiritualSanctuary(Listener):
    """At each player's upkeep, if that player controls a Plains, they gain 1 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if 'plains' in gs.card_filter.on_player_board(event.active_player).plains().result():
            gs.score_mgr.increment_life(event.active_player, 1, source, gs)


class StormWorld(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is 4 minus the number of cards in their hand"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        card_cnt = len(gs.hands[gs.turn_mgr.player_turn_idx].cards)
        if card_cnt > 4:
            gs.apply_damage(source, card_cnt - 4, gs.turn_mgr.player_turn_idx)


class TheAbyss(Listener):
    """At each upkeep, destroy target nonartifact creature that player controls of their choice. No regeneration."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = event.active_player
        your_non_art_creatures = gs.card_filter.on_player_board(p_id).non_artifact_creatures().result()
        if not your_non_art_creatures:
            return
        if len(your_non_art_creatures) == 1:
            gs.action_stack.push(DestroyAction(p_id, gs, source, your_non_art_creatures[0], False), gs, False)
        gs.action_stack.push(TheAbyssAction(p_id, gs, source), gs, False)


class TheRack(Listener):
    """At opponent's upkeep, this artifact deals X damage to that player, X = 3 - len(hand) [X can't be negative]"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.hands[opp_id].cards)
        if opp_hand_len < 3:
            gs.apply_damage(s, 3 - opp_hand_len, opp_id)


class TheTabernacleAtPendrellVale(Listener):
    """All creatures have 'At your upkeep, destroy this creature unless you pay {1}.'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_creature in gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).creatures().result():
            gs.action_stack.push(PayManaOrSacUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, your_creature, '1'))


class VesuvanDoppelgangerUpkeep(Listener):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options, copy_color=False)


class YawgmothDemon(Listener):
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


# --- ZONE CHANGE ---
class AnkhOfMishra(Listener):
    """Whenever a land enters, this artifact deals 2 damage to that land's controller"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class CitanulDruid(Listener):
    """Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or 'Artifact' not in event.card.props.card_types:
            return
        source.counters.add_counter(PLUS_ONE)


class DingusEgg(Listener):
    """Whenever a land is put into a graveyard from battlefield, deal 2 damage to that land's controller."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.GRAVEYARD or event.from_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class FieldOfDreams(Listener):
    """Players play with the top card of their libraries revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if Zone.LIBRARY not in (event.to_zone, event.from_zone):
            return
        player_idx = event.card.owner_id
        if gs.libraries[player_idx]:
            gs.libraries[player_idx][0].reveal()


class GoblinShrineOnLeave(Listener):
    """... When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.from_zone != Zone.BATTLEFIELD or event.card.props.slug != 'goblin-shrine':
            return
        for goblin in gs.card_filter.in_play().by_sub_type('Goblin').creatures().result():
            gs.apply_damage(event.card, 1, goblin)


class Kismet(Listener):
    """Artifacts, creatures, and lands your opponents control enter tapped"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, s: GameCard, event: ZoneChangeEvent):
        if event.card.owner_id != flip(s.owner_id) or event.to_zone != Zone.BATTLEFIELD:
            return
        artifacts = gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result()
        creatures = gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
        lands = gs.card_filter.on_player_board(flip(s.owner_id)).lands().result()
        if event.card not in artifacts + creatures + lands:
            return
        gs.tap_card(event.card)


class LandEquilibrium(Listener):
    """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
    that player instead puts that land onto the battlefield then sacrifices a land of their choice"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id == event.card.owner_id or event.card not in gs.card_filter.land().result():
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if len(opp_lands) < your_land_cnt:
            return
        gs.action_stack.push(SacChoice(event.card.owner_id, gs, source, opp_lands), gs, False)


class MoldDemonETB(Listener):
    """When this creature enters, sacrifice this creature unless you sacrifice two Swamps"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.to_zone != Zone.BATTLEFIELD:
            return
        your_swamps = gs.card_filter.on_player_board(source.owner_id).swamps().result()
        if len(your_swamps) < 2:
            gs.destroy(event.card, False)
        gs.action_stack.push(MoldDemonChoice(gs.turn_mgr.player_turn_idx, gs, source, your_swamps), gs, False)


class Revelation(Listener):
    """Players play with their hands revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.HAND:
            return
        event.card.reveal()


class StanggOnLeave(Listener):
    """Exile that Stangg Twin token when Stangg leaves the battlefield; sacrific Stangg when Stangg Twin LTB"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.card.props.slug not in ('stangg', 'stangg-twin') or event.card.owner_id != source.owner_id:
            return
        if event.from_zone != Zone.BATTLEFIELD:
            return
        other_slug = 'stangg-twin' if event.card.props.slug == 'stangg' else 'stangg'
        other_card = gs.card_filter.on_player_board(event.card.owner_id).by_slug(other_slug).result()[0]
        gs.destroy(other_card)


class VerduranEnchantress(Listener):
    """Whenever you cast an enchantment spell, you may draw a card"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id != event.card.owner_id or event.card not in gs.card_filter.enchantments().result():
            return
        gs.action_stack.push(DrawCardsOrDontChoice(source.owner_id, gs, source), gs, False)
