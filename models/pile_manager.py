from __future__ import annotations
from copy import copy
import random
from typing import TYPE_CHECKING

from models.events_all import ZoneChangeEvent, DiesEvent, DiscardEvent, DrawCardEvent, StateBasedEvent
from models.hand import Hand
from models.modifiers import RegenerationMod
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

class PileManager:
    """Handles card location & movement across piles"""
    def __init__(self, gs: GameState):
        self._gs = gs
        self.libraries: list[list[GameCard]] = self._gs.all_player_cards.copy()
        self.boards: list[list[GameCard]] = [[] for _ in range(self._gs.player_cnt)]
        self.graveyards: list[list[GameCard]] = [[] for _ in range(self._gs.player_cnt)]
        self.exiles: list[list[GameCard]] = [[] for _ in range(self._gs.player_cnt)]
        self.hands: list[Hand] = [Hand(sort_pref=Hand.SortOrient.L_TO_R) for _ in range(self._gs.player_cnt)]
        
        # GameCard getting reference to GameState is a ChatGPT suggestion
        for lib in self.libraries:
            for c in lib:
                c.game_state = self

    def move_card(self, card: GameCard, to_zone: Zone, *, cause: str | None = None, emit_zone_event: bool = True):
        if card.zone == to_zone:
            return

        from_zone = copy(card.zone)

        # Unregister effects, remove all mods if leaving battlefield
        if card.zone == Zone.BATTLEFIELD:
            self._leave_battlefield(card, to_zone)

        self._remove_from_zone(card, card.zone)
        self._add_to_zone(card, to_zone)
        card.zone = to_zone
        if emit_zone_event:
            self._gs.event_mgr.emit(ZoneChangeEvent(card, from_zone, to_zone, cause), self)

        # Post-move hooks
        # self._after_zone_change(card, from_zone, to_zone)

    def destroy(self, card: GameCard, allow_regeneration: bool = True):
        print('Entering destroy() for', card)
        # ask replacement system if destruction is prevented
        # as of now, this destruction replacement & damage are handled separately but could be unified later
        if allow_regeneration:
            shield = next(card.modifiers.iter_type(RegenerationMod), None)
            if shield:
                card.modifiers.remove(shield)
                card.tapped = True
                card.damage_received_this_turn = 0
                self._gs.remove_from_combat(card)
                print(f'{card} is regenerated')
                return

        self._gs.event_mgr.emit(DiesEvent(card), self)
        self.move_card(card, Zone.GRAVEYARD, cause="destroy")
        self._gs.cards_that_died_this_turn.append(card)
        print(f'{card} is destroyed')
        self._gs.game_history.append_non_action(self._gs, card=card, text=f'{card} is destroyed')

    def exile(self, card: GameCard):
        self.move_card(card, Zone.EXILE, cause="exile")
        print(f'{card} is exiled')
        self._gs.game_history.append_non_action(self._gs, card=card, text=f'{card} is exiled')

    def bounce(self, card: GameCard):
        self.move_card(card, Zone.HAND, cause="bounce")
        print(f'{card} is bounced')
        self._gs.game_history.append_non_action(self._gs, card=card, text=f'{card} is bounced')

    def discard(self, card: GameCard, source: GameCard | None = None):
        self._gs.event_mgr.emit(DiscardEvent(card.orig_owner_id, card, source), self)
        self.move_card(card, Zone.GRAVEYARD, cause="discard")
        print(f'{card} is discarded')
        self._gs.game_history.append_non_action(self._gs, card=card, text=f'{card} is bounced')

    def reanimate(self, card: GameCard):
        self.move_card(card, Zone.BATTLEFIELD, cause='reanimate')
        print(f'{card} is reanimated')
        self._gs.game_history.append_non_action(self._gs, card=card, text=f'{card} is renimated')

    def cast(self, card: GameCard):
        self.move_card(card, Zone.BATTLEFIELD, cause='cast')
        print(f'{card} is cast')
        self._gs.game_history.append_non_action(self._gs, card=card, text=f'{card} is cast')

    def draw(self, p_id: int, cnt: int = 1):
        for _ in range(cnt):
            self.move_card(self._gs.pile_mgr.libraries[p_id][0], Zone.HAND, cause='draw')
            self._gs.event_mgr.emit(DrawCardEvent(p_id), self)
            print(f'Player #{p_id} draws')
            self._gs.game_history.append_non_action(self._gs, text=f'Player #{p_id} draws')

    def _add_to_zone(self, card: GameCard, zone: Zone):
        if card.is_token and zone != Zone.BATTLEFIELD:
            return
        match zone:
            case Zone.BATTLEFIELD:
                card.reveal()
                self._gs.pile_mgr.boards[card.owner_id].append(card)
                card.turn_entered_for_owner = self._gs.turn_mgr.turn_number
            case Zone.HAND:
                self._gs.pile_mgr.hands[card.orig_owner_id].cards.append(card)
                self._gs.pile_mgr.hands[card.orig_owner_id].sort_cards()
            case Zone.GRAVEYARD:
                card.reveal()
                self._gs.pile_mgr.graveyards[card.orig_owner_id].append(card)
            case Zone.EXILE:
                card.reveal()
                self._gs.pile_mgr.exiles[card.orig_owner_id].append(card)
            case Zone.LIBRARY:
                self._gs.pile_mgr.libraries[card.orig_owner_id].insert(0, card)

    def _remove_from_zone(self, card: GameCard, zone: Zone):
        match zone:
            case Zone.BATTLEFIELD:
                self._gs.pile_mgr.boards[card.owner_id].remove(card)
                if card.is_tapped:
                    card.is_tapped = False
            case Zone.HAND:
                self._gs.pile_mgr.hands[card.orig_owner_id].cards.remove(card)
                self._gs.pile_mgr.hands[card.orig_owner_id].sort_cards()
            case Zone.GRAVEYARD:
                self._gs.pile_mgr.graveyards[card.owner_id].remove(card)
            case Zone.EXILE:
                self._gs.pile_mgr.exiles[card.owner_id].remove(card)
            case Zone.LIBRARY:
                self._gs.pile_mgr.libraries[card.owner_id].remove(card)

    def _leave_battlefield(self, card: GameCard, to_zone: Zone):
        """Emit ZoneChangeEvent before unregistering its effects, doing so for the subject card;
        detach all attached GameCard auras; call GameCard.clear_all_mods()"""
        self._gs.event_mgr.emit(ZoneChangeEvent(card, card.zone, to_zone, cause='leave'), self)
        self._gs.event_mgr.unregister_effects(card)

        for aura in list(card.auras):
            self._gs.event_mgr.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'), self)
            self.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
            self._gs.event_mgr.unregister_effects(aura)
        card.clear_all_mods()
        self._gs.event_mgr.emit(StateBasedEvent(), self)
