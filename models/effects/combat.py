from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from models.counter_tokens import PLUS_ONE
from models.effects.counters import AddCounterAtEndStep
from models.effects.destroy_sac_regenerate import DestroyAtCombatEnd
from models.effects.until_end_of_turn import TowerOfCoireallEOT, UnblockableEOT
from models.events_all import BlockEvent, CombatEndEvent, AttackEvent, DamageResolvedEvent, DiesEvent
from models.modifiers import KWAMod, PTMod

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Effect

# --- GENERICS ---
class UnblockableThisTurn(Effect):
    """Target creature can't be blocked this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = UnblockableEOT(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))

# --- CARD-SPECIFIC ---
class Abomination(Effect):
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

class AbuJafar(Effect):
    """When this creature dies, destroy all creatures blocking or blocked by it. They can't be regenerated."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if event.card is not source:
            return
        for com in gs.combats:
            for other_combatant in com.get_combatants_against(event.card):
                gs.destroy(other_combatant, allow_regeneration=False)

class CavePeopleAttackPump(Effect):
    """Whenever this creature attacks, it gets +1/-2 until end of turn ..."""
    listens_to = AttackEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker is not s:
            return
        event.attacker.modifiers.items.append(PTMod(s=s, p_adj=1, t_adj=-2, expires='EOT'))

class CockatriceAndThicketBasilisk(Effect):
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

class ElderLandWurm(Effect):
    """When this creature blocks for the first time, it loses defender"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.blocker is not s:
            return
        s.modifiers.items.append(KWAMod(s=s, add_or_remove='remove', kwa='Defender'))

class GiantShark(Effect):
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
            s.modifiers.items.append(PTMod(s=s, p_adj=2, expires='EOT'))
            s.modifiers.items.append(KWAMod(s=s, add_or_remove='add', kwa='Trample', expires='EOT'))

class GlyphOfDoom(Effect):
    """On cast, select a wall.  Register GlyphOfDoomListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = GlyphOfDoomListener(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))

class GlyphOfDoomListener(Effect):
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

class GlyphOfLife(Effect):
    """On cast, select a wall.  Register GlyphOfLifeListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = GlyphOfLifeListener(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))

class GlyphOfLifeListener(Effect):
    """Registered by GlyphOfLife. Whenever that wall is dealt damage by an attacker this turn, gain that much life."""
    listens_to = DamageResolvedEvent

    def __init__(self, the_wall: GameCard):
        self.the_wall = the_wall

    def on_event(self, gs: GameState, s: GameCard, event: DamageResolvedEvent):
        if event.target is not self.the_wall or not event.is_combat:
            return
        gs.score_mgr.increment_life(s.owner_id, event.amt, s, gs)

class InfernalMedusa(Effect):
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

class InfiniteAuthority(Effect):
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

class Sentinel(Effect):
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
        s.modifiers.items.append(PTMod(s=s, p_adj=0, t_adj=new_t - s.toughness))

class TimeElementalAttackedOrBlocked(Effect):
    """When this creature attacks or blocks, at end of combat, sacrifice it & it deals 5 damage to you"""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if s not in gs.card_filter.combatants().result():
            return
        gs.apply_damage(s, 5, s.owner_id)
        gs.destroy(s)

class TowerOfCoireall(Effect):
    """{T}: Target creature can't be blocked by Walls this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = TowerOfCoireallEOT(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))

class Venom(Effect):
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
