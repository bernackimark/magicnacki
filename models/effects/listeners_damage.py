from __future__ import annotations
from typing import TYPE_CHECKING, Any

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.constants import KW
from models.game_card.counter_tokens import PLUS_ONE, VITALITY
from models.effects.base import Listener
from models.events_all import DamageProposedEvent, DamageResolvedEvent
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
        if event.target != self.protected_player or KW.FLYING in event.source.keyword_abilities:
            return
        event.prevented += event.remaining
        event.remaining = 0

class BloodOfTheMartyr(Listener):
    """Until EOT, if damage would be dealt to any creature, you may have that damage dealt to you instead"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if not event.target.is_creature:
            return
        # from models.actions.damage import RedirectDamageToYouAction
        options = [CO(f'Redirect all damage from {event.target} to you', lambda: self.redirect(source, event))]
        # options = [RedirectDamageToYouAction(source.owner_id, gs, source, event)]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    @staticmethod
    def redirect(source: GameCard, event: DamageProposedEvent):
        event.target = source.owner_id

class Forcefield(Listener):
    """(1): Next time an unblocked creature of your choice would deal you combat damage this turn, reduce damage to 1"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self):
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent):
        if self.is_expired:
            return
        if event.target != source.owner_id or event.source is not self.target or not event.is_combat:
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

class MartyrsOfKorlis(Listener):
    """As long as this creature is untapped, redirect all damage dealt to you by artifacts to this creature instead"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source.owner_id or source.is_tapped or 'Artifact' not in event.source.card_types:
            return
        source.damage_received_this_turn += event.remaining
        event.prevented += event.remaining
        event.remaining = 0

class ReverseDamage(Listener):
    """The next time a source of your choice would deal damage to you this turn, prevent that damage.
    You gain life equal to the damage prevented this way."""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self):
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.source is not self.target:
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
        if event.target != self.protected_player or KW.FLYING not in event.source.keyword_abilities:
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

class EyeForAnEye(Listener):
    """The next time a source of your choice would deal damage to you this turn, also deal damage to source's owner."""
    listens_to = DamageResolvedEvent
    expires = 'EOT'

    def __init__(self):
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent) -> None:
        if self.is_expired or event.source is not self.target or event.target != source.owner_id:
            return
        self.is_expired = True
        gs.apply_damage(source, event.amt, event.source.owner_id)


class FungusaurOnDamage(Listener):
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(PLUS_ONE)

class GlyphOfLife(Listener):
    """Whenever target wall is dealt damage by an attacker this turn, gain that much life."""
    listens_to = DamageResolvedEvent
    expires = 'EOT'

    def __init__(self):
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        self.target = targets[0]

    def on_event(self, gs: GameState, s: GameCard, event: DamageResolvedEvent):
        if event.target is not self.target or not event.is_combat:
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
        opp_cards = gs.pile_mgr.hands[opp_id]
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
        opp_cards = gs.pile_mgr.hands[opp_id]
        if not opp_cards:
            return
        for c in opp_cards:
            gs.pile_mgr.discard(c, source)

class SpiritLink(Listener):
    """Whenever host deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.host and event.amt > 0:
            gs.score_mgr.increment_life(source.owner_id, event.amt, source, gs)
