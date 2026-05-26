from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import PLUS_ONE
from models.effects.base import Effect
from models.effects.listens_for_end_step import AddCounterAtEndStep
from models.effects.listens_for_combat_end import DestroyAtCombatEnd
from models.events_all import BlockEvent
from models.modifiers import KWAMod, PTMod

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


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


class AislingLeprechaun(Effect):
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
