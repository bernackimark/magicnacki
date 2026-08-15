from __future__ import annotations

from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction, ChoiceOption
from models.game_card.counter_tokens import PLUS_ONE
from models.effects.base import Listener
from models.events_all import ZoneChangeEvent
from models.utils import flip
from models.constants import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class AnkhOfMishra(Listener):
    """Whenever a land enters, this artifact deals 2 damage to that land's controller"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class CitanulDruid(Listener):
    """Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or 'Artifact' not in event.card.props.card_types:
            return
        source.counters.add_counter(PLUS_ONE)


class DingusEgg(Listener):
    """Whenever a land is put into a graveyard from battlefield, deal 2 damage to that land's controller."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.GRAVEYARD or event.from_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class FieldOfDreams(Listener):
    """Players play with the top card of their libraries revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if Zone.LIBRARY not in (event.to_zone, event.from_zone):
            return
        player_idx = event.card.owner_id
        if gs.pile_mgr.libraries[player_idx]:
            gs.pile_mgr.libraries[player_idx][0].reveal()


class GoblinShrineOnLeave(Listener):
    """... When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        print('AAA')
        if event.card is not source or event.from_zone != Zone.BATTLEFIELD:
            print('ABC', event.card, source, event.from_zone)
            return
        print('BBB')
        for goblin in gs.card_filter.in_play().by_sub_type('Goblin').creatures().result():
            gs.apply_damage(event.card, 1, goblin)


class HazezonTamarLTB(Listener):
    """When HT LTB, ALL permanents with BOTH the Sand AND Warrior types are exiled, not just those it created"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        if event.from_zone != Zone.BATTLEFIELD or event.card is not source:
            return
        for sand_warrior in gs.card_filter.in_play().by_sub_type('Sand').by_sub_type('Warrior').result():
            gs.pile_mgr.destroy(sand_warrior, allow_regeneration=False)


class Kismet(Listener):
    """Artifacts, creatures, and lands your opponents control enter tapped"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, s: GameCard, event: ZoneChangeEvent):
        if event.card.owner_id != flip(s.owner_id) or event.to_zone != Zone.BATTLEFIELD:
            return
        artifacts = gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result()
        creatures = gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
        lands = gs.card_filter.on_player_board(flip(s.owner_id)).lands().result()
        if event.card not in artifacts + creatures + lands:
            return
        event.card.tap()


class LandEquilibrium(Listener):
    """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
    that player instead puts that land onto the battlefield then sacrifices a land of their choice"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id == event.card.owner_id or 'Land' not in event.card.card_types:
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if len(opp_lands) < your_land_cnt:
            return
        options = [ChoiceOption(f'Sac {land}', lambda: gs.pile_mgr.sacrifice(land)) for land in opp_lands]
        # options = [Sac(event.card.owner_id, gs, land) for land in opp_lands]
        gs.queue_choice(ChoiceAction(options))

class Revelation(Listener):
    """Players play with their hands revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.HAND:
            return
        event.card.reveal()

class StanggOnLeave(Listener):
    """Exile that Stangg Twin token when Stangg leaves the battlefield; sacrific Stangg when Stangg Twin LTB"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.card.props.slug not in ('stangg', 'stangg-twin') or event.card.owner_id != source.owner_id:
            return
        if event.from_zone != Zone.BATTLEFIELD:
            return
        other_slug = 'stangg-twin' if event.card.props.slug == 'stangg' else 'stangg'
        other_card = next(c for c in gs.pile_mgr.boards[source.owner_id] if c.props.slug == other_slug)
        gs.event_mgr.unregister_specific_effect(self)
        gs.pile_mgr.destroy(other_card)

class TawnossCoffinZoneChange(Listener):
    """When this artifact LTB, return its exiled card to the battlefield tapped with the noted number &
     kind of counters on it and re-attach all auras.
     Note: all of this code is repeated in TawnossCoffinUntap"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        if event.card is not source or event.to_zone == Zone.BATTLEFIELD:
            return
        exiled_card: GameCard = source.extras.get('exiled_card')
        deep_copy: GameCard = source.extras.get('exiled_card_deep_copy')
        exiled_card.tap()
        for ctr in deep_copy.counters:
            exiled_card.counters.add_counter(ctr)
        for aura in deep_copy.modifiers.items:
            if isinstance(aura, GameCard):
                exiled_card.modifiers.append(aura)


class TheWretchedUnsteal(Listener):
    """... gain control of creatures UNTIL Wretched LTB or you don't control Wretched."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        # TODO: Since a ZoneChangeEvent doesn't capture steals ...
        #  if The Wretched itself is stolen, I still need to return the stolen creatures
        if event.card is not source or event.from_zone != Zone.BATTLEFIELD:
            return

        from models.game_card.modifiers import OwnershipMod
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.modifiers.get(OwnershipMod, reverse=True):
                if mod.s is source:
                    c.modifiers.remove(mod)
                    gs.pile_mgr.boards[source.owner_id].remove(c)
                    gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                    break
