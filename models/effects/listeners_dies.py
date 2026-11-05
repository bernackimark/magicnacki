from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO, pay_mana_to_draw_cards, pay_mana_to_bounce, pay_mana_to_gain_life
from models.game_card.counter_tokens import PLUS_ONE, MINUS_ZERO_ONE
from models.effects.base import Listener, GenTrig
from models.events_all import DiesEvent, DamageResolvedEvent, Event, UpkeepEvent
from models.game_card.modifiers import BasePTMod, SubTypeMod
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class AxelrodGunnarson(Listener):
    """Whenever a creature dealt damage by AG this turn dies, you gain 1 life & AG deals 1 damage to [opponent]"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent):
            if e.source is not source or e.target is not event.card:
                continue
            gs.score_mgr.increment_life(source.owner_id, 1, source)
            gs.apply_damage(source, 1, event.card.owner_id)
            return

class BlazingEffigy(Listener):
    """When this creature dies, it deals X damage to target creature.
    X is 3 plus the amount of damage dealt to this creature this turn by other sources named Blazing Effigy."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, s: GameCard, event: DiesEvent) -> None:
        if s is not event.card:
            return
        all_creatures = gs.card_filter.creatures().in_play().result()
        if not all_creatures:
            return
        total_damage = 3 + sum([e.amt for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent)
                                if e.target is s and e.source.props.slug == 'blazing-effigy'])
        options = [CO(f'{s.props.name} deals {total_damage} damage to {t}',
                      lambda: gs.apply_damage(s, total_damage, t)) for t in all_creatures]
        gs.choice_mgr.queue(ChoiceAction(options))

class BrineHag(Listener):
    """When BH dies, change base PT of all creatures that dealt damage to it this turn to 0/2
    for as long as that creature remains on the battlefield;
    however, State-based rules do evaluate & the creature will almost definitely die"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source:
            return
        events: list[DamageResolvedEvent] = gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent)
        for e in events:
            if e.target is not source or not e.source.is_creature:
                continue
            e.source.modifiers.append(BasePTMod(0, 2, s=source))

class CreatureBond(Listener):
    """When enchanted creature dies, deal damage = to host's toughness to the creature's controller"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source.host:
            return
        gs.apply_damage(source, source.host.toughness, source.host.owner_id)

class FirestormPhoenix(Listener):
    """If this card would die, bounce it instead; it cannot be re-summoned this turn"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source:
            return
        gs.pile_mgr.bounce(source)
        from models.effects.listeners_permission import CantCastEOT
        gs.event_mgr.register(CantCastEOT(source), source)

class LichDies(Listener):
    """... When L is put into a graveyard from the battlefield, you lose the game ..."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source:
            return
        gs.is_game_over = True
        gs.winner = flip(source.owner_id)

class PersonalIncarnationDies(Listener):
    """... When this creature dies, its owner loses half their life, rounding up the loss amount"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card is not source:
            return
        reduce_life_by = math.ceil(gs.life[source.owner_id] / 2)
        gs.apply_damage(source, reduce_life_by, source.owner_id)

class PuppetMaster(Listener):
    """When host dies, bounce host instead. You may pay {UUU} to bounce this aura."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source.host:
            return
        gs.pile_mgr.bounce(event.card)
        if gs.mana_pools[source.owner_id].can_pay('UUU'):
            options = [CO(f"Pay {{{'UUU'}}} to bounce {source}",
                          lambda: pay_mana_to_bounce(gs, source.owner_id, 'UUU', source))]
            gs.choice_mgr.queue(ChoiceAction(options, may=True))

class Reincarnation(Listener):
    """Choose target creature. When that creature dies this turn, reanimate a creature from that creature's graveyard"""
    listens_to = DiesEvent
    expires = 'EOT'

    def __init__(self):
        self.target_creature: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, target: list[GameCard | int]):
        self.target_creature = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not self.target_creature:
            return
        creatures_in_that_gy = [c for c in gs.graveyards[event.card.owner_id] if c.is_creature and c is not event.card]
        if not creatures_in_that_gy:
            return
        options = [CO(f'Reanimate {card}', lambda c=card: gs.pile_mgr.reanimate(c)) for card in creatures_in_that_gy]
        gs.choice_mgr.queue(ChoiceAction(options))

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
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent):
            if e.source is not source or e.target is not event.card:
                continue
            source.counters.add_counter(PLUS_ONE)
            return

class TakklemaggotHostDies(LichDies):
    """... When host dies, that creature's controller chooses a creature T could enchant.
    If they can, return T to the battlefield under your control attached to that creature.
    If they can't, return T to the battlefield under your control as a non-Aura enchantment &
    it loses 'enchant creature' and gains 'At host's upkeep, T deals 1 damage to that player.'"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source.host:
            return
        print("Inside TakkleHostDies")
        targets = [c for c in gs.card_filter.in_play().creatures().result()
                   if gs.perm_querier.can_target(c, source) and c is not source.host]
        if not targets:
            print('I have no more legal targets; I should be converting into a non-aura enchantment')
            self._reanimate_and_convert_to_non_aura(gs, source)
            return
        options = [CO(f'Attach {source.props.name} to {t}',
                   lambda tar=t: self._reanimate_and_attach(gs, source, tar)) for t in targets]
        gs.choice_mgr.queue(ChoiceAction(options))

    def _reanimate_and_attach(self, gs: GameState, takkle: GameCard, host: GameCard):
        """Reanimate, attach;
        Re-register the 0/-1 Upkeep Listener (originally register by the card's definition),
        Re-register this Listener class"""
        from models.effects.resolvers_generic import Attach
        print('Inside reanimate & attach, attaching to', host)
        gs.pile_mgr.reanimate(takkle)
        a = Attach()
        a.resolve(gs, takkle, host)
        from models.game_card.effect_spec_templates import On
        from models.game_card.event_conditions import EC
        from models.effects.resolvers_generic import AddCounter
        from models.game_card.target_funcs import ET
        listener = GenTrig(On(UpkeepEvent).where(EC().is_host_turn()).then(AddCounter(MINUS_ZERO_ONE)).t(ET.host()))
        gs.event_mgr.register(listener.effect, takkle)
        gs.event_mgr.register(self, takkle)

    @staticmethod
    def _reanimate_and_convert_to_non_aura(gs: GameState, takkle: GameCard):
        gs.pile_mgr.reanimate(takkle)
        print("Takkle's zone is", takkle.zone)
        takkle.modifiers.append(SubTypeMod(s=takkle, add_or_remove='remove', item='Aura'))
        print('Inside Takkle, should now not have Aura in its sub_types', takkle.card_sub_types)
        from models.game_card.effect_spec_templates import On
        from models.game_card.event_conditions import EC
        from models.effects.resolvers_generic import DealDamage
        from models.game_card.target_funcs import ET
        listener = GenTrig(On(UpkeepEvent).where(EC().is_host_turn()).then(DealDamage(1, to=ET.s_owner())))
        gs.event_mgr.register(listener.effect, takkle)
