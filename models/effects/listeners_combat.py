from __future__ import annotations
from typing import TYPE_CHECKING, Any

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.constants import KW
from models.effects.listeners_permission import WallOfDustAttackerCantAttackNextTurn
from models.effects.base import Listener
from models.events_all import AttackEvent, BlockEvent, CombatEndEvent, UnblockedAttackerEvent, CombatBeginEvent
from models.game_card.modifiers import PTMod, KWAMod
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

# --- ATTACK EVENT ---
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
