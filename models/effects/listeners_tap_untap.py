from __future__ import annotations
from typing import TYPE_CHECKING

from models.actions.special import TimeVaultSkipTurnAction
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import MINUS_ZERO_TWO
from models.effects.base import Listener
from models.events_all import TapCardEvent, UntapCardEvent, UntapPhaseEvent, Event
from models.modifiers import KWAMod

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


# --- TAP CARD EVENT ---
class ArtifactPossessionTap(Listener):
    """Enchant artifact Whenever host becomes tapped ... deal 2 damage to host's controller"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent) -> None:
        if event.card is not source.host:
            return
        gs.apply_damage(source, 2, source.host.owner_id)

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

class HauntingWindTap(Listener):
    """Whenever an artifact becomes tapped ... deal 1 damage to artifact's controller"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent) -> None:
        if not event.card.is_artifact:
            return
        gs.apply_damage(source, 1, event.card.owner_id)

class JohanOnTap(Listener):
    """If J becomes tapped, your creatures lose the Vigilance granted by J"""
    listens_to = TapCardEvent
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent) -> None:
        if event.card is not source:
            return
        for c in gs.card_filter.on_player_board(source.owner_id).creatures().result():
            for mod in c.modifiers.iter_type_reverse(KWAMod):
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
        from models.actions.special import Attach
        options = [Attach(s.host.owner_id, gs, s, land) for land in host_owner_lands]
        gs.pending_choice = ChoiceAction(options)


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

class PowerleechTap(Listener):
    """Whenever an opponent's artifact becomes tapped ... you gain 1 life"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent) -> None:
        if source.owner_id == event.card.owner_id or not event.card.is_artifact:
            return
        gs.score_mgr.increment_life(source.owner_id, 1, source, gs)

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


# --- UNTAP CARD EVENT ---
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
        options = [TimeVaultSkipTurnAction(source.owner_id, gs, source)]
        gs.pending_choice = ChoiceAction(options, may=True)
