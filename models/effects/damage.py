from __future__ import annotations
import math
from typing import Optional, TYPE_CHECKING

from models.counter_tokens import VITALITY, PLUS_ONE
from models.events_all import DamageResolvedEvent, DiesEvent, ZoneChangeEvent, TapCardEvent, UpkeepEvent, \
    EndStepEvent, DrawStepEvent
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.choice_actions_all import ElderSpawnUpkeepChoice, CurseArtifactUpkeepChoice, LordOfThePitUpkeepChoice
from models.damage import PreventNextDamage, DamageEvent
from models.effects.base import Effect
from models.utils import flip


# --- GENERICS ---
class DealDamage(Effect):
    def __init__(self, amt: int = None):  # None is permitted due to the possibility of variable X
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: GameCard | int = None, variable_amt: int = None):
        print(source, self.amt, target)
        amt = self.amt if not variable_amt else variable_amt
        gs.apply_damage(source, amt, target)

class DealOneDamageToTargetList(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard | int] = None):
        for t in target:
            print(source, 1, target)
            gs.apply_damage(source, 1, t)

class DealDamageToOwnerOnUpkeep(Effect):
    listens_to = UpkeepEvent

    def __init__(self, amount: int):
        self.amount = amount

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.apply_damage(source, self.amount, source.owner_id)

class DealDamageOnHostUpkeep(Effect):
    listens_to = UpkeepEvent

    def __init__(self, amount: int):
        self.amount = amount

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.apply_damage(source, self.amount, source.host.owner_id)

class DealDamageToAllCreaturesAndPlayers(Effect):
    def __init__(self, amt: int):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        [gs.apply_damage(source, self.amt, p_id, is_combat=False) for p_id in (0, 1)]
        [gs.apply_damage(source, self.amt, creature) for creature in gs.card_filter.in_play().creatures().result()]

class DealDamageToTargetAndSelf(Effect):
    def __init__(self, amt_to_target: int, amt_to_source_card: int):
        self.amt_to_target = amt_to_target
        self.amt_to_source_card = amt_to_source_card

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a target")
        gs.apply_damage(source, self.amt_to_target, target)
        gs.apply_damage(source, self.amt_to_source_card, source)

class DealDamageToTargetAndYou(Effect):
    def __init__(self, amt_to_target: int, amt_to_you: int):
        self.amt_to_target = amt_to_target
        self.amt_to_you = amt_to_you

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a target")
        gs.apply_damage(source, self.amt_to_target, target)
        gs.apply_damage(source, self.amt_to_you, source.owner_id)

class PreventAllCombatDamageThisTurn(Effect):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        prevention = PreventNextDamage(source, combat_only=True)
        gs.damage_preventions.append(prevention)
        gs.register_effect_until_eot(prevention)

class PreventNextDamageToCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """target = the GameCard being protected"""
        gs.damage_preventions.append(PreventNextDamage(source, target_card=target))

# --- CARD-SPECIFIC ---
class AnkhOfMishra(Effect):
    """Whenever a land enters, this artifact deals 2 damage to that land's controller"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)

class Backfire(Effect):
    """Whenever host deals damage to you, this Aura deals that much damage to that creature's controller"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.host and event.target == source.owner_id:
            gs.apply_damage(source, event.amt, source.host.owner_id)

class Banshee(Effect):
    """{X}, {T}: This creature deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        damage_to_target = s.variable_x // 2
        damage_to_you = s.variable_x - damage_to_target
        gs.apply_damage(s, damage_to_target, t)
        gs.apply_damage(s, damage_to_you, s.owner_id)
        s.variable_x = None

class BlackVise(Effect):
    """As opponent's upkeep, this artifact deals X damage to that player, X is = cards in their hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.hands[opp_id].cards)
        if opp_hand_len > 4:
            gs.apply_damage(s, opp_hand_len - 4, opp_id)

class CityOfBrassDamageOnTap(Effect):
    """Whenever this land becomes tapped, it deals 1 damage to you"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if event.card is not source:
            return
        gs.apply_damage(source, 1, source.owner_id)

class CreatureBond(Effect):
    """When enchanted creature dies, deal damage = to host's toughness to the creature's controller"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source.host:
            return
        gs.apply_damage(source, source.host.toughness, source.host.owner_id)

class CurseArtifact(Effect):
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(CurseArtifactUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)

class DingusEgg(Effect):
    """Whenever a land is put into a graveyard from battlefield, deal 2 damage to that land's controller."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.GRAVEYARD or event.from_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)

class Earthquake(Effect):
    """Earthquake deals X damage to each creature without flying and each player"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        for c in gs.card_filter.in_play().has('Flying', False).creatures().result():
            gs.apply_damage(source, x, c)
        for p_id in (0, 1):
            gs.apply_damage(source, x, p_id)

class ElderSpawnUpkeep(Effect):
    """At YOUR upkeep, sac an Island or sac this creature & it deals 6 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(ElderSpawnUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, s), gs, False)

class ErgRaiders(Effect):
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id or s.has_summoning_sickness:
            return
        if s not in gs.card_filter.attackers().result():
            gs.apply_damage(s, 2, s.owner_id)

class EternalFlame(Effect):
    """X = # of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = len(gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).mountains().result())
        gs.apply_damage(source, x, flip(gs.turn_mgr.player_turn_idx))
        gs.apply_damage(source, math.ceil(x/2), gs.turn_mgr.player_turn_idx)

class EyeForAnEye(Effect):
    """The next time a source of your choice would deal damage to you this turn, also deal damage to source's owner."""
    # Handling this in an interesting way to work within current framework:
    # Prevent all damage via gs.damage_preventions, then apply the damage here via the callback
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        """target = the GameCard doing the original damage"""
        def deal_damage(prevented: int):
            gs.apply_damage(t, prevented, s.owner_id)
            gs.apply_damage(s, prevented, t.owner_id)

        gs.damage_preventions.append(
            PreventNextDamage(s, None, target_player=s.owner_id, source_card=t, on_prevent=deal_damage))

class FungusaurOnDamage(Effect):
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(PLUS_ONE)

class GaseousForm(Effect):
    """Prevent all combat damage that would be dealt this turn by enchanted creature and each creature blocking it."""
    # TODO: THIS IS ALL DAMAGE ALWAYS.  DO I HANDLE THIS SOMEWHERE IN DAMAGE PREVENTION?
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the enchanted attacker"""
        the_combat = [com for com in gs.combats if com.attacker == target]
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
        for b in the_combat[0].blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))

class GoblinShrineOnLeave(Effect):
    """... When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.from_zone != Zone.BATTLEFIELD or event.card.props.slug != 'goblin-shrine':
            return
        for goblin in gs.card_filter.in_play().by_sub_type('Goblin').creatures().result():
            gs.apply_damage(event.card, 1, goblin)

class JovialEvil(Effect):
    """deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        # target = opponent_id
        opp_white_creature_cnt = len(gs.card_filter.on_player_board(target).creatures().result())
        gs.apply_damage(source, opp_white_creature_cnt * 2, target)

class Karma(Effect):
    """At each player's upkeep, this enchantment deals damage to that player = number of Swamps they control."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        swamp_cnt = len(gs.card_filter.on_player_board(event.active_player).swamps().result())
        if swamp_cnt:
            gs.apply_damage(source, swamp_cnt, event.active_player)

class LivingArtifactOnDamage(Effect):
    """Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura ...
    You can target opponent artifacts. The controller of the Aura controls the Living Artifact ability"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(VITALITY)

class LordOfThePitUpkeep(Effect):
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

class ManaVaultDamageIfTapped(Effect):
    """... At your draw step, if this artifact is tapped, it deals 1 damage to you ..."""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: DrawStepEvent):
        if event.active_player != s.owner_id or not s.is_tapped:
            return
        gs.apply_damage(s, 1, s.owner_id)

class PersonalIncarnation(Effect):
    """... When this creature dies, its owner loses half their life, rounding up the loss amount"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        reduce_life_by = math.ceil(gs.score_mgr.life[source.owner_id] / 2)
        gs.apply_damage(source, reduce_life_by, source.owner_id)

class PowerSurge(Effect):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is the number of untapped lands they controlled at the beginning of this turn"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        untapped_lands = gs.card_filter.in_play().untapped().lands().result()
        if untapped_lands:
            gs.apply_damage(source, len(untapped_lands), gs.turn_mgr.player_turn_idx)

class RukhEgg(Effect):
    """When this creature dies, create a 4/4 red Bird creature token with flying at next end step"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        from special import CreateTokenCreature
        obj = CreateTokenCreature('rukh')
        obj.resolve(gs, source)
        # gs.create_token_creature(source.owner_id, 'Bird', 4, 4, ['Flying', 'Attack'], [], ['Bird'], 'R')

class Sandstorm(Effect):
    """Sandstorm deals 1 damage to each attacking creature.
    [from Google: it only hits creatures already attacking when it resolves.]"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for attacker in gs.card_filter.attackers().result():
            gs.apply_damage(source, 1, attacker)

class StormSeeker(Effect):
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""
    def resolve(self, gs: GameState, source: GameCard, t: Optional[GameCard] = None):
        opp_idx = flip(source.owner_id)
        gs.apply_damage(source, len(gs.hands[opp_idx].cards), opp_idx)

class StormWorld(Effect):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is 4 minus the number of cards in their hand"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        card_cnt = len(gs.hands[gs.turn_mgr.player_turn_idx].cards)
        if card_cnt > 4:
            gs.apply_damage(source, card_cnt - 4, gs.turn_mgr.player_turn_idx)

class TheRack(Effect):
    """At opponent's upkeep, this artifact deals X damage to that player, X = 3 - len(hand) [X can't be negative]"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.hands[opp_id].cards)
        if opp_hand_len < 3:
            gs.apply_damage(s, 3 - opp_hand_len, opp_id)

class Tracker(Effect):
    """Tracker deals damage = its power to target creature. That creature deals damage = its power to this creature."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.apply_damage(source, source.power, target)
        gs.apply_damage(target, target.power, source)

class Typhoon(Effect):
    """Typhoon deals damage to opponent = the number of Islands that player controls"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        opp = flip(gs.turn_mgr.player_turn_idx)
        opp_island_cnt = len(gs.card_filter.on_player_board(opp).islands().result())
        if opp_island_cnt:
            gs.apply_damage(s, opp_island_cnt, opp)
