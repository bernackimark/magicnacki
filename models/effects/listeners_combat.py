from __future__ import annotations
from typing import TYPE_CHECKING, Any

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.constants import KW, Zone
from models.game_card.counter_tokens import PLUS_ONE_ZERO
from models.effects.base import Listener
from models.effects.listeners_generic import DestroyAtCombatEnd
from models.events_all import AttackEvent, BlockEvent, CanAttackQueryEvent, CombatEndEvent, CanBlockQueryEvent, \
    CastResolvedEvent, ZoneChangeEvent, UnblockedAttackerEvent, CombatBeginEvent
from models.game_card.modifiers import PTMod, KWAMod
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

# --- ATTACK EVENT ---
class HasranOgress(Listener):
    """Whenever this creature attacks, it deals 3 damage to you unless you pay {2}"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        if not gs.mana_pools[s.owner_id].can_pay('2'):
            gs.apply_damage(s, 3, s.owner_id)
            return
        options = [CO(f"Pay {{{'2'}}}", lambda: gs.mana_pools[s.owner_id].pay('2')),
                   CO(f'{s} deals 3 damage to you', lambda: gs.apply_damage(s, 3, s.owner_id))]
        gs.choice_mgr.queue(ChoiceAction(options))

class MijaeDjinn(Listener):
    """Whenever this creature attacks, flip a coin. If you lose the flip, remove this creature from combat and tap it"""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: AttackEvent):
        if event.attacker is not s:
            return
        result = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        print(f'The result of the random event was: {result}')
        if result == 'tails':
            gs.combat_mgr.remove_from_combat(s)
            s.tap()


# --- BLOCK EVENT ---
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
            s.modifiers.append(KWAMod(s=s, item=KW.TRAMPLE, expires='EOT'))

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
            gs.combat_mgr.remove_from_combat(s)


# --- CAN ATTACK QUERY EVENT ---
class Arboria(Listener):
    """Creatures can only attack a player who, in their last turn,
    cast a spell or put a nontoken permanent onto the battlefield"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        opp = flip(event.attacker.owner_id)
        p_most_recent_turn = gs.turn_mgr.most_recent_turn_started[opp]
        events_on_players_last_turn = gs.event_mgr.get_events(p_most_recent_turn)
        for e in events_on_players_last_turn:
            if isinstance(e, CastResolvedEvent) and e.owner_id == opp and not e.card.is_land:
                return
            if (isinstance(e, ZoneChangeEvent) and e.card.owner_id == opp and not e.card.is_land
                    and not e.card.is_token and e.to_zone == Zone.BATTLEFIELD):
                return
        event.permission = False

class GoblinRockSledCanAttack(Listener):
    """This creature can't attack unless defending player controls a Mountain"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if not gs.card_filter.in_play().mountains().on_player_board(flip(source.owner_id)).result():
            event.permission = False

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
        # TODO: this needs expires = 'After Owner Next Turn'


# --- CAN BLOCK QUERY EVENT ---
class Lure(Listener):
    """All creatures able to block host do so"""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source.host:
            return
        if gs.perm_querier.can_block(event.blocker, event.attacker):
            event.permission = True

class MarblePriestForcesBlock(Listener):
    """All Walls able to block this creature do so ..."""
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        if event.attacker is not source or 'Wall' not in event.blocker.card_sub_types:
            return
        if gs.perm_querier.can_block(event.blocker, event.attacker):
            event.permission = True

# --- COMBAT BEGIN EVENT ---
class Johan(Listener):
    """At your combat begin step, you may have J gain Defender & your creatures gain Vigilance EOT.
    If J becomes tapped, your creatures lose their Vigilance."""
    listens_to = CombatBeginEvent

    def on_event(self, gs: GameState, source: GameCard, event: CombatBeginEvent) -> None:
        options = [CO(f'{source} gains Defender & your creatures gain Vigilance until end of turn',
                      lambda: self.johan(gs, source))]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    @staticmethod
    def johan(gs: GameState, s: GameCard):
        from models.effects.listeners_tap_untap import JohanOnTap
        s.modifiers.append(KWAMod(s=s, item='Defender', expires='EOT'))
        for c in gs.card_filter.on_player_board(s.owner_id).creatures().result():
            c.modifiers.append(KWAMod(s=s, item=KW.VIGILANCE, expires='EOT'))
        gs.event_mgr.register(JohanOnTap(), s)

# --- COMBAT END EVENT ---
class GlyphOfDoom(Listener):
    """At combat end, destroy creature blocked by target wall this turn."""
    listens_to = CombatEndEvent
    expires = 'EOT'

    def __init__(self):
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        self.target = targets[0]

    def on_event(self, gs: GameState, s: GameCard, event: CombatEndEvent):
        if attacker := next((c for c in gs.combat_mgr.get_combatants_against(self.target)), None):
            gs.pile_mgr.destroy(attacker)
            self.is_expired = True

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
        gs.pile_mgr.sacrifice(s)

class TheWretched(Listener):
    """At combat end, gain control of all creatures blocking this creature for as long as you control TW.
    Note: The blocker must have survived."""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, source: GameCard, event: CombatEndEvent) -> None:
        from models.effects.resolvers_generic import Steal
        wretched_blockers = [b for com in gs.combat_mgr.combats for b in com.blockers if com.attacker is source]
        if not wretched_blockers:
            return
        for blocker in wretched_blockers:
            if blocker not in gs.card_filter.in_play().result():
                continue
            Steal().resolve(gs, source, blocker)


# --- UNBLOCKED ---
class FloralSpuzzem(Listener):
    """Whenever this creature walks, you may destroy target opp artifact instead of dealing the combat damage."""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker is not s:
            return
        opp_artifacts = gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result()
        if not opp_artifacts:
            return
        options = [CO(f'Destroy {t} & forego combat damage assigned by {s}',
                      lambda: self.destroy_and_forego_combat_damage(gs, s, t))
                   for t in opp_artifacts]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    @staticmethod
    def destroy_and_forego_combat_damage(gs: GameState, s: GameCard, t: GameCard):
        from models.effects.listeners_generic import PreventNextDamageBy
        gs.pile_mgr.destroy(t)
        gs.event_mgr.register(PreventNextDamageBy(s, combat_only=True))
