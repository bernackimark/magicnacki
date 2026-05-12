from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from models.choice_actions_all import DrawCardsOrDontChoice, DiscardChoice, ShuffleOrDontChoice, SearchLibraryChoice
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.draw_discard import DiscardCard
from models.effects.base import Effect
from models.utils import flip

from models.events_all import EndStepEvent, ZoneChangeEvent, DamageResolvedEvent, DrawStepEvent, DiscardEvent, \
    DiscardStepEvent, Event


# --- GENERIC ---
class DrawCards(Effect):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        if target is None:
            return
        gs.draw(target, self.card_cnt)

class Discard(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.pending_choice = DiscardChoice(target, gs, source, target)

class RevealLibrary(Effect):
    def __init__(self, viewer_id: int | None = None, top_x: int | None = None):
        self.viewer_id = viewer_id
        self.top_x = top_x

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if self.viewer_id is None:
            self.viewer_id = source.owner_id
        cards = gs.libraries[source.owner_id] if not self.top_x else gs.libraries[source.owner_id][:self.top_x]
        gs.add_presentation_request(self.viewer_id, 'view_library', {'cards': cards})

# --- CARD-SPECIFIC ---
class BazaarOfBaghdad(Effect):
    """Draw two cards, then discard three cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.draw(source.owner_id, 2)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id, 3, 3)

class Braingeyser(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is not None:
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            gs.draw(target, x)

class CursedRackEffect(Effect):
    """Opponent's maximum hand size is four [at their discard phase]"""
    listens_to = DiscardStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        opp_id = flip(source.owner_id)
        if gs.turn_mgr.player_turn_idx != opp_id:
            return

        hand = gs.hands[opp_id]
        for i in range(len(hand.cards) - 4):
            gs.action_stack.push(DiscardCard(opp_id, gs, hand.cards[0]), gs, False)

class DemonicTutor(Effect):
    """Search your library for a card, put that card into your hand, then shuffle"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = source.owner_id
        gs.pending_choice = SearchLibraryChoice(p_id, gs, source, list(gs.libraries[p_id]), Zone.HAND)

class FieldOfDreams(Effect):
    """Players play with the top card of their libraries revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if Zone.LIBRARY not in (event.to_zone, event.from_zone):
            return
        player_idx = event.card.owner_id
        if gs.libraries[player_idx]:
            gs.libraries[player_idx][0].reveal()

class GlassesOfUrza(Effect):
    """Look at opponent's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        for c in gs.hands[flip(source.owner_id)].cards:
            c.reveal()

class GwendlynDiCorci(Effect):
    """{T}: Target player discards a card at random. Activate only during your turn"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        cards = gs.hands[target].cards
        if not cards:
            return
        if len(cards) == 1:
            gs.discard(cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, cards)
        gs.discard(random_card, source)

class HowlingMine(Effect):
    """At each player's draw step, if this artifact is untapped, that player draws an additional card"""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent):
        if source.is_tapped:
            return
        gs.draw(event.active_player)

class HypnoticSpecter(Effect):
    """Whenever this creature deals damage to an opponent, that player discards a card at random"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp_id = flip(source.owner_id)
        if event.source is not source or event.target is not opp_id:
            return
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) == 1:
            gs.discard(opp_cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
        gs.discard(random_card, source)

class JalumTome(Effect):
    """Draw a card, then discard a card"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.draw(source.owner_id)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id)

class MindTwist(Effect):
    """Target player discards X cards at random"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        opp_id = flip(source.owner_id)
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) <= x:
            for c in opp_cards:
                gs.discard(c, source)
            return
        for _ in range(x):
            random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
            gs.discard(random_card, source)

class NicolBolas(Effect):
    """Whenever this creature deals damage to an opponent, that player discards their hand"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp_id = flip(source.owner_id)
        if event.source is not source or event.target is not opp_id:
            return
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        for c in opp_cards:
            gs.discard(c, source)

class PsychicPurgeDiscard(Effect):
    """... When a spell or ability an opponent controls causes you to discard this card, that player loses 5 life"""
    listens_to = DiscardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        if not event.source or event.source.owner_id != source.owner_id:
            return
        gs.apply_damage(source, 5, event.source.owner_id)

class RagMan(Effect):
    """Opponent reveals their hand and discards a creature card at random. Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        opp_cards = gs.hands[target].cards
        for c in opp_cards:
            c.reveal()
        opp_creatures = [c for c in opp_cards if c.is_creature]
        if not opp_creatures:
            return
        if len(opp_creatures) == 1:
            gs.discard(opp_creatures[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, opp_creatures)
        gs.discard(random_card, source)

class Revelation(Effect):
    """Players play with their hands revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.HAND:
            return
        event.card.reveal()

class VerduranEnchantress(Effect):
    """Whenever you cast an enchantment spell, you may draw a card"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id != event.card.owner_id or event.card not in gs.card_filter.enchantments().result():
            return
        gs.action_stack.push(DrawCardsOrDontChoice(source.owner_id, gs, source), gs, False)

class Visions(Effect):
    """Look at the top five cards of target player's library. You may then have that player shuffle that library."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        for c in gs.libraries[target].cards[:5]:
            print('Showing you', c)
        gs.pending_choice = ShuffleOrDontChoice(target, gs, source, gs.libraries[target].cards)

class WheelOfFortune(Effect):
    """Each player discards their hand, then draws seven cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for i in (0, 1):
            [DiscardCard(i, gs, card).play() for card in gs.hands[i].cards]
            gs.draw(i, 7)
