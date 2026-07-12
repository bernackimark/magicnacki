from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import PLUS_ONE, VITALITY
from models.effects.base import Listener
from models.events_all import DamageProposedEvent, DamageResolvedEvent, Event
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


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

class ForethoughtAmulet(Listener):
    """If an instant or sorcery source would deal 3 or more damage to you, it deals 2 damage to you instead"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source.owner_id or event.remaining < 3:
            return
        if not event.source.is_instant and not event.source.is_sorcery:
            return
        prevention_amt = event.amt - 2
        event.prevented += prevention_amt
        event.remaining -= prevention_amt

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
        source.damage_received_this_turn += event.remaining
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
        iterations = min(event.remaining, counter_cnt)
        for _ in range(iterations):
            source.counters.remove_counter(PLUS_ONE)
            event.prevented += 1
            event.remaining -= 1

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
    expires = 'EOT'

    def __init__(self, the_wall: GameCard):
        self.the_wall = the_wall

    def on_event(self, gs: GameState, s: GameCard, event: DamageResolvedEvent):
        if event.target is not self.the_wall or not event.is_combat:
            return
        gs.score_mgr.increment_life(s.owner_id, event.amt, s, gs)
        self.is_expired = True


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
