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
    DrawCardsOrDontChoice, GabrielAngelfireChoice, GiantSlugChoice
from models.counter_tokens import PLUS_ONE, VITALITY, PIN, MINUS_ZERO_TWO, WIND
from models.effects.base import Listener
from models.effects.listeners_generic import DestroyAtCombatEnd, AddCounterAtEndStep
from models.effects.resolvers_generic import Steal
from models.events_all import AttackEvent, BlockEvent, CombatEndEvent, DamageResolvedEvent, DiesEvent, DiscardEvent, \
    DiscardStepEvent, DrawCardEvent, DrawStepEvent, EndStepEvent, LifeLossEvent, StateBasedEvent, TapCardEvent, \
    UnblockedAttackerEvent, UntapPhaseEvent, UpkeepEvent, Event, ZoneChangeEvent, DamageProposedEvent, CostQueryEvent, \
    CanAttackQueryEvent
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
            s.tap()


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
        gs.event_mgr.register(delayed, s)
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
        gs.event_mgr.register(delayed, s)
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
        effect = DestroyAtCombatEnd(self.the_wall, event.attacker)
        gs.event_mgr.register(effect, self.the_wall)

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
        gs.event_mgr.register(delayed, s)
        # this will later get unregistered at combat end

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
        gs.event_mgr.register(delayed, s)
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

class WallOfDust(Listener):
    """Whenever this creature blocks, the attacker can't attack during its controller's next turn"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, source: GameCard, event: BlockEvent) -> None:
        if event.blocker is not source:
            return
        gs.event_mgr.register(WallOfDustAttackerCantAttackNextTurn(event.attacker), source)

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

class WallOfDustAttackerCantAttackNextTurn(Listener):
    """... can't attack during its controller's next turn"""
    listens_to = CanAttackQueryEvent

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if event.attacker is not self.target:
            return
        event.permission = False
        gs.event_mgr.unregister_specific_effect(self)

# --- COMBAT END ---
class InfiniteAuthorityCombatEnd(Listener):
    """At combat end, if host is in combat with a creature with toughness <= 3, destroy the other creature ..."""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, source: GameCard, event: CombatEndEvent) -> None:
        if not source.host or source.host not in gs.card_filter.combatants().result():
            return
        for other_creature in gs.card_filter.combating_against(source.host).result():
            if other_creature.toughness <= 3:
                gs.pile_mgr.destroy(other_creature)

class TimeElementalAttackedOrBlocked(Listener):
    """When this creature attacks or blocks, at end of combat, sacrifice it & it deals 5 damage to you"""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if s not in gs.card_filter.combatants().result():
            return
        gs.apply_damage(s, 5, s.owner_id)
        gs.pile_mgr.destroy(s)

class TheWretchedSteal(Listener):
    """At combat end, gain control of all creatures blocking this creature for as long as you control this creature"""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, source: GameCard, event: CombatEndEvent) -> None:
        # TODO: are the blockers already in the graveyard?
        wretched_blockers = [b for com in gs.combats for b in com.blockers if com.attacker is source]
        if not wretched_blockers:
            return
        from .resolvers_generic import Steal
        for blocker in wretched_blockers:
            Steal(Zone.BATTLEFIELD).resolve(gs, source, blocker)

# --- COST QUERY EVENT ---
class Gloom(Listener):
    """White spells cost {3} more to cast. Activated abilities of white enchantments cost {3} more to activate."""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.mana import ManaCost
        if (not (event.query == 'cast' and 'W' in event.card.colors) and not
           ('W' in event.card.colors and 'Enchantment' in event.card.card_types)):
            return
        event.cost = ManaCost(event.cost) + ManaCost('3')

class ManaMatrix(Listener):
    """Instant and enchantment spells you cast cost {2} less to cast"""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.mana import ManaCost
        if event.query != 'cast' or event.player_id != s.owner_id:
            return
        if 'Instant' not in event.card.card_types and 'Enchantment' not in event.card.card_types:
            return
        event.cost = ManaCost(event.cost) - ManaCost('3')

class PlanarGate(Listener):
    """Creature spells you cast cost {2} less to cast"""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.mana import ManaCost
        if event.query != 'cast' or event.player_id != s.owner_id or not event.card.is_creature:
            return
        event.cost = ManaCost(event.cost) - ManaCost('2')

class PowerArtifact(Listener):
    """Enchant artifact Enchanted artifact's activated abilities cost {2} less to activate.
    This effect can't reduce the mana in that cost to less than one mana."""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.mana import ManaCost
        if event.query != 'activate' or event.card.host is not s:
            return
        event.cost = ManaCost(event.cost) - ManaCost('2')  # TODO: minimum '1' or a colored equivalent

class StoneCalendar(Listener):
    """Spells you cast cost {1} less to cast"""
    listens_to = CostQueryEvent

    def on_event(self, gs: GameState, s: GameCard, event: CostQueryEvent):
        from models.mana import ManaCost
        if event.query != 'cast' or event.player_id != s.owner_id:
            return
        event.cost = ManaCost(event.cost) - ManaCost('1')

# --- DAMAGE PROPOSED EVENT ---
class AlAbarasCarpetPrevention(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_player: int):
        self.protected_player = protected_player

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target != self.protected_player or 'Flying' in event.source.keyword_abilities:
            return
        event.prevented += event.remaining
        event.remaining = 0

class ArgothianPixies(Listener):
    """Prevent all damage that would be dealt to this creature by artifact creatures"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source:
            return
        if 'Artifact' not in event.source.card_types or 'Creature' not in event.source.props.card_types:
            return
        event.prevented += event.remaining
        event.remaining = 0

class ArgothianTreefolkPrevention(Listener):
    """Prevent all damage that would be dealt to this creature by artifact sources"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source:
            return
        if 'Artifact' not in event.source.card_types:
            return
        event.prevented += event.remaining
        event.remaining = 0


class ArtifactWardPrevention(Listener):
    """Prevent all damage that would be dealt to enchanted creature by artifact sources"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source.host:
            return
        event.prevented += event.remaining
        event.remaining = 0

class ForcefieldPrevention(Listener):
    listens_to = DamageProposedEvent

    def __init__(self, creature: GameCard, protected_player: int):
        self.creature = creature
        self.protected_player = protected_player

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent):
        if self.is_expired:
            return
        if event.target != self.protected_player or event.source is not self.creature or not event.is_combat:
            return

        if event.remaining > 1:
            event.prevented += event.remaining - 1
            event.remaining = 1

        self.is_expired = True

class GaseousForm(Listener):
    """Prevent all combat damage that would be dealt this turn by enchanted creature and each creature blocking it."""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if source.host not in (event.source, event.target) or not event.is_combat:
            return
        event.prevented += event.remaining
        event.remaining = 0

class MarblePriestPrevention(Listener):
    """Prevent all combat damage that would be dealt to this creature by Walls"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source or not event.is_combat or 'Wall' not in event.source.card_sub_types:
            return
        event.prevented += event.remaining
        event.remaining = 0

class MartyrsOfKorlis(Listener):
    """As long as this creature is untapped, redirect all damage dealt to you by artifacts to this creature instead"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source.owner_id or source.is_tapped or 'Artifact' not in event.source.card_types:
            return
        event.prevented += event.remaining
        event.remaining = 0

class ReverseDamageEOT(Listener):
    """The next time a source of your choice would deal damage to you this turn, prevent that damage.
    You gain life equal to the damage prevented this way."""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_dealer: GameCard):
        self.damage_dealer = damage_dealer

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.source is not self.damage_dealer:
            return
        the_damage_amt = event.remaining
        event.prevented += event.remaining
        event.remaining = 0
        self.is_expired = True
        gs.score_mgr.increment_life(source.owner_id, the_damage_amt, source, gs)

class RockHydraAutoDamagePrevent(Listener):
    """For each 1 damage that would be dealt to this creature, if it has a +1/+1 counter on it,
    remove a +1/+1 counter from it and prevent that 1 damage."""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source:
            return
        counter_cnt = source.counters.get_count(PLUS_ONE)
        if not counter_cnt:
            return
        source.counters.remove_counter(PLUS_ONE, counter_cnt)
        event.prevented += counter_cnt
        event.amt -= counter_cnt

class ScarecrowPrevention(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_player: int):
        self.protected_player = protected_player

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target != self.protected_player or 'Flying' not in event.source.keyword_abilities:
            return
        event.prevented += event.remaining
        event.remaining = 0

class UncleIstvanPrevention(Listener):
    """Prevent all damage that would be dealt to this creature by creatures"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source or 'Creature' not in event.source.card_types:
            return
        event.prevented += event.remaining
        event.remaining = 0

class VeteranBodyguard(Listener):
    """As long as VB is untapped, redirect all damage by unblocked creatures to VB instead"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if source.is_tapped or event.target != source.owner_id or not event.is_combat:
            return
        if event.source in gs.card_filter.unblocked_attackers().result():
            event.target = source

# --- DAMAGE RESOLVED EVENT ---
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

class EyeForAnEyeEOT(Listener):
    """The next time a source of your choice would deal damage to you this turn, also deal damage to source's owner."""
    listens_to = DamageResolvedEvent
    expires = 'EOT'

    def __init__(self, damage_dealer: GameCard, damage_receiving_player: int):
        self.damage_dealer = damage_dealer
        self.damage_receiving_player = damage_receiving_player

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent) -> None:
        if self.is_expired or event.source is not self.damage_dealer or event.target != self.damage_receiving_player:
            return
        self.is_expired = True
        gs.apply_damage(source, event.amt, self.damage_dealer.owner_id)

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
        opp_cards = gs.pile_mgr.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) == 1:
            gs.pile_mgr.discard(opp_cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
        gs.pile_mgr.discard(random_card, source)


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
        opp_cards = gs.pile_mgr.hands[opp_id].cards
        if not opp_cards:
            return
        for c in opp_cards:
            gs.pile_mgr.discard(c, source)

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
                gs.pile_mgr.destroy(other_combatant, allow_regeneration=False)

class AxelrodGunnarson(Listener):
    """Whenever a creature dealt damage by AG this turn dies, you gain 1 life & AG deals 1 damage to [opponent]"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        for e in gs.turn_mgr.events:
            if not isinstance(e, DamageResolvedEvent):
                continue
            if e.source is not source or e.target is not event.card:
                continue
            gs.score_mgr.increment_life(source.owner_id, 1, source, gs)
            gs.apply_damage(source, 1, event.card.owner_id)
            return

class BlazingEffigy(Listener):
    """When this creature dies, it deals X damage to target creature.
    X is 3 plus the amount of damage dealt to this creature this turn by other sources named Blazing Effigy."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if source is not event.card:
            return
        all_creatures = gs.card_filter.creatures().in_play().result()
        if not all_creatures:
            return
        total_damage = 3 + sum([e.amt for e in gs.turn_mgr.events if isinstance(e, DamageResolvedEvent)
                                and e.target is source and e.source.props.slug == 'blazing-effigy'])
        # TODO: How do I get the target creature from the user?

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
        gs.pile_mgr.exile(source)


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
    expires = 'EOT'

    def __init__(self, target_creature: GameCard):
        self.target_creature = target_creature

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != self.target_creature:
            return
        gs.pile_mgr.destroy(source)
        self.is_expired = True

class SengirVampire(Listener):
    """Whenever a creature dealt damage by this creature this turn dies, put a +1/+1 counter on this creature"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        for e in gs.turn_mgr.events:
            if not isinstance(e, DamageResolvedEvent):
                continue
            if e.source is not source or e.target is not event.card:
                continue
            source.counters.add_counter(PLUS_ONE)
            return

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

        hand = gs.pile_mgr.hands[opp_id]
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
        gs.pile_mgr.draw(event.active_player)


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
            gs.pile_mgr.destroy(s, allow_regeneration=False)

class ErgRaiders(Listener):
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id or s.has_summoning_sickness:
            return
        if s not in gs.card_filter.attackers().result():
            gs.apply_damage(s, 2, s.owner_id)

class InfiniteAuthorityEndStep(Listener):
    """At end step, if [that other] creature was destroyed [this] way, put a +1/+1 counter on host."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        from models.events_all import DiesEvent
        if not source.host:
            return
        other_combatants = gs.card_filter.combating_against(source.host).result()
        for e in gs.turn_mgr.events:
            if isinstance(e, DiesEvent) and e.card in other_combatants:
                source.host.counters.add_counter(PLUS_ONE)

class PestilenceEndStep(Listener):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if not gs.card_filter.creatures().in_play().result():
            gs.pile_mgr.destroy(source)

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
            gs.pile_mgr.destroy(creature)

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
        gs.pile_mgr.destroy(source)

class WhirlingDervish(Listener):
    """At each end step, if this creature dealt damage to an opponent this turn, put a +1/+1 counter on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        from models.events_all import DamageResolvedEvent
        for e in gs.turn_mgr.events:
            if isinstance(e, DamageResolvedEvent) and e.source is source and e.target == flip(source.owner_id):
                source.counters.add_counter(PLUS_ONE)
                return

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
            gs.pile_mgr.destroy(source)


class SerendibDjinnNoLands(Listener):
    """When you control no lands, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            print(f'Player #{source.owner_id} has no lands, so Serendib Djinn is destroyed')
            gs.pile_mgr.destroy(source)


# --- TAP EVENT ---
class Blight(Listener):
    """Enchant land; When enchanted land becomes tapped, destroy it."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if not source.host or source.props.slug != 'blight' or event.card is not source.host:
            return
        gs.pile_mgr.destroy(source.host)


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

class TimeVaultOption(Listener):
    """If you would begin your turn while this artifact is tapped, you may skip that turn instead."""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent) -> None:
        if source.owner_id != event.active_player or not source.is_tapped:
            return
        from models.choice_actions_all import TimeVaultChoice
        gs.action_stack.push(TimeVaultChoice(source.owner_id, gs, source), False)

# --- UPKEEP ---
class BlackVise(Listener):
    """As opponent's upkeep, this artifact deals X damage to that player, X is = cards in their hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.pile_mgr.hands[opp_id].cards)
        if opp_hand_len > 4:
            gs.apply_damage(s, opp_hand_len - 4, opp_id)

class CosmicHorror(Listener):
    """At your upkeep, destroy unless you pay {3BBB}. If destroyed this way, it deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if not gs.mana_pools[source.owner_id].can_pay('3BBB'):
            gs.pile_mgr.destroy(source)
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
            gs.pile_mgr.destroy(source, False)
        gs.action_stack.push(CycloneChoice(source.owner_id, gs, source), gs, False)

class DemonicHordesUpkeep(Listener):
    """... At your upkeep, pay {BBB} or tap this creature and sacrifice a land of an opponent's choice"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            source.tap()
        elif len(your_lands) == 1:
            source.tap()
            gs.pile_mgr.destroy(your_lands[0])
        elif not gs.mana_pools[source.owner_id].can_pay('BBB'):
            gs.action_stack.push(OpponentDestroysLandChoice(flip(source.owner_id), gs, source))
        else:
            gs.action_stack.push(DemonicHordesUpkeepChoice(source.owner_id, gs, source), gs, False)

class DropOfHoney(Listener):
    """At your upkeep, destroy the creature with the least power. It can't be regenerated.
    If two or more creatures are tied for least power, you choose one. When there are no creatures on the battlefield,
    sac Drop of Honey."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        creatures = gs.card_filter.creatures().in_play().result()
        if not creatures:
            gs.pile_mgr.destroy(source, allow_regeneration=False)
            return

        min_power = min([c.power for c in creatures])
        creatures_w_min_power = [c for c in creatures if c.power == min_power]

        if len(creatures_w_min_power) == 1:
            gs.pile_mgr.destroy(creatures_w_min_power[0], allow_regeneration=False)
            return

        from models.choice_actions_all import DestroyChoice
        gs.pending_choice = DestroyChoice(source.owner_id, gs, source, creatures_w_min_power, allow_regen=False)

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

class GabrielAngelfire(Listener):
    """At your upkeep, choose flying, first strike, trample, rampage 3. GA gains that ability until your next upkeep."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = GabrielAngelfireChoice(s.owner_id, gs, s)

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

class GiantSlug(Listener):
    """At your next upkeep, this creature gains landwalk of your choice until the end of that turn."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = GiantSlugChoice(s.owner_id, gs, s)

class HazezonTamarTokenCreation(Listener):
    """Create X 1/1 Sand Warrior tokens at your next upkeep; X is the number of lands you control at that time"""
    listens_to = UpkeepEvent

    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return

        from .resolvers_generic import CreateTokenCreature
        for _ in gs.card_filter.lands().on_player_board(self.owner_id).result():
            CreateTokenCreature('sand-warrior').resolve(gs, source)

        gs.event_mgr.unregister_specific_effect(self)

class IvoryTower(Listener):
    """At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = source.owner_id
        if p_id != event.active_player:
            return
        if (hand_size := len(gs.pile_mgr.hands[p_id].cards)) > 4:
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
            gs.pile_mgr.destroy(source)
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
            gs.pile_mgr.destroy(source)
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
        card_cnt = len(gs.pile_mgr.hands[gs.turn_mgr.player_turn_idx].cards)
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
        opp_hand_len = len(gs.pile_mgr.hands[opp_id].cards)
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
    """At your upkeep, Sac an artifact, or tap this creature, and it deals 2 damage to you"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if source.owner_id != gs.turn_mgr.player_turn_idx:
            return
        if not gs.card_filter.on_player_board(source.owner_id).artifacts().result():
            source.tap()
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
        if gs.pile_mgr.libraries[player_idx]:
            gs.pile_mgr.libraries[player_idx][0].reveal()

class GoblinShrineOnLeave(Listener):
    """... When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.from_zone != Zone.BATTLEFIELD or event.card.props.slug != 'goblin-shrine':
            return
        for goblin in gs.card_filter.in_play().by_sub_type('Goblin').creatures().result():
            gs.apply_damage(event.card, 1, goblin)

class HazezonTamarLTB(Listener):
    """When HT LTB, ALL permanents with BOTH the Sand AND Warrior types are exiled, not just those it created"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        if event.from_zone != Zone.BATTLEFIELD or event.card is not source:
            return
        for sand_warrior in gs.card_filter.in_play().by_sub_type('Sand').by_sub_type('Warrior').result():
            gs.pile_mgr.destroy(sand_warrior, allow_regeneration=False)

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
        event.card.tap()

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
            gs.pile_mgr.destroy(event.card, False)
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
        gs.pile_mgr.destroy(other_card)

class TheWretchedUnsteal(Listener):
    """... gain control of creatures UNTIL Wretched LTB or you don't control Wretched."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        # TODO: Since a ZoneChangeEvent doesn't capture steals ...
        #  if The Wretched itself is stolen, I still need to return the stolen creatures
        if event.card is not source or event.from_zone is not Zone.BATTLEFIELD:
            return

        from models.modifiers import OwnershipMod
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod) and mod.s is source:
                    c.modifiers.remove(mod)
                    gs.pile_mgr.boards[source.owner_id].remove(c)
                    gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                    break

class VerduranEnchantress(Listener):
    """Whenever you cast an enchantment spell, you may draw a card"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id != event.card.owner_id or event.card not in gs.card_filter.enchantments().result():
            return
        gs.action_stack.push(DrawCardsOrDontChoice(source.owner_id, gs, source), gs, False)
