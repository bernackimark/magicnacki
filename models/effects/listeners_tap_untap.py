from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.game_card.counter_tokens import MINUS_ZERO_TWO
from models.effects.base import Listener
from models.events_all import TapCardEvent, UntapCardEvent, UntapPhaseEvent, CanUntapAtUntapQueryEvent, Event
from models.game_card.modifiers import KWAMod
from models.systems.phase import Phase

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


# --- TAP CARD EVENT ---
class JohanOnTap(Listener):
    """If J becomes tapped, your creatures lose the Vigilance granted by J"""
    listens_to = TapCardEvent
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent) -> None:
        if event.card is not source:
            return
        for c in gs.card_filter.on_player_board(source.owner_id).creatures().result():
            for mod in c.modifiers.get(KWAMod, reverse=True):
                if mod.s is source:
                    c.modifiers.remove(mod)
                    break
        self.is_expired = True

class Kudzu(Listener):
    """When enchanted land becomes tapped, destroy it.
    That land's controller must attach this Aura to a land of their choice. If they own no lands, destroy Kudzu."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent) -> None:
        if event.card is not s.host:
            return
        gs.pile_mgr.destroy(event.card)  # Note: this may cause the aura to be sent to the graveyard already
        host_owner_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if not host_owner_lands:
            gs.pile_mgr.destroy(s)
            return
        if len(host_owner_lands) == 1:
            s.host = host_owner_lands[0]
            s.host.auras.append(s)
            return
        options = [CO(f'Attach {s} to {land}', lambda: self.attach(s, land)) for land in host_owner_lands]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def attach(aura: GameCard, host: GameCard):
        aura.host = host
        host.auras.append(aura)


# --- UNTAP CARD EVENT ---
class PhyrexianGremlinsUntaps(Listener):
    """{T}: Tap target artifact. It doesn't untap during its controller's untap step so long as PG remains tapped."""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapCardEvent) -> None:
        if event.card is not source:
            return
        cant_untap_listeners = gs.event_mgr.event_listeners.get(CanUntapAtUntapQueryEvent, [])
        for listener in cant_untap_listeners:
            if listener.source is source:
                gs.event_mgr.unregister_specific_effect(listener.effect)
                break

class TawnossCoffinUntap(Listener):
    """When this artifact ... becomes untapped, return its exiled card to the battlefield tapped with the noted number &
     kind of counters on it and re-attach all auras.
     Note: all of this code is repeated in TawnossCoffinZoneChange"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapCardEvent) -> None:
        if event.card is not source:
            return
        exiled_card: GameCard = source.extras.get('exiled_card')
        deep_copy: GameCard = source.extras.get('exiled_card_deep_copy')
        exiled_card.tap()
        for ctr in deep_copy.counters:
            exiled_card.counters.add_counter(ctr)
        for aura in deep_copy.modifiers.items:
            if isinstance(aura, GameCard):
                exiled_card.modifiers.append(aura)


# --- UNTAP PHASE ---
class DampingField(Listener):
    """Players can't untap more than one artifact during their untap steps."""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent):
        if source.owner_id != event.active_player:
            return
        tapped_artifacts = [c for c in gs.card_filter.on_player_board(event.active_player).artifacts().result()
                            if c.is_tapped]
        if len(tapped_artifacts) <= 1:
            return

        options = [CO(f"Untap {card}", lambda card=card: self.untap_selected(gs, tapped_artifacts, card))
                   for card in tapped_artifacts]
        options.append(CO("Leave all artifacts tapped", lambda: self.leave_all_tapped(gs, tapped_artifacts)))
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def untap_selected(gs: GameState, artifacts: list[GameCard], selected: GameCard):
        selected.untap()
        for card in artifacts:
            gs.turn_mgr.untap_decisions_made.add(card.id_)

    @staticmethod
    def leave_all_tapped(gs: GameState, artifacts: list[GameCard]):
        for card in artifacts:
            gs.turn_mgr.untap_decisions_made.add(card.id_)

class RasputinDreamweaverUntap(Listener):
    """... At your upkeep, if RD started the turn (as proxied w the UntapPhaseEvent) untapped &
    w < 7 dream counters on it, put a dream counter on it."""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent) -> None:
        source.extras['started_turn_untapped'] = not source.is_tapped

class TimeVaultOption(Listener):
    """If you would begin your turn while this artifact is tapped, you may skip that turn instead."""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent) -> None:
        if source.owner_id != event.active_player or not source.is_tapped:
            return
        options = [CO(f'Skip turn and untap {source}', lambda: self.untap_and_skip_turn(gs, source))]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    @staticmethod
    def untap_and_skip_turn(gs: GameState, c: GameCard):
        c.untap()
        gs.phase_mgr.set_phase(Phase.PASS_THE_TURN)
