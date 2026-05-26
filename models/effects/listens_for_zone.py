from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import DrawCardsOrDontChoice, SacChoice, MoldDemonChoice
from models.counter_tokens import PLUS_ONE
from models.modifiers import OwnershipMod

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Effect
from models.effects.piles import Steal
from models.events_all import ZoneChangeEvent
from models.utils import flip
from models.zone import Zone


class StealCardLeaves(Effect):
    """You control enchanted creature; must return if Control Magic leaves board"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        print(source, event, f'The host {event.card.host} belongs to player #{event.card.host.owner_id if event.card.host else "no host"}')
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        host = event.card.host
        Steal().resolve(gs, source, host)
        print('I think I returned control to', flip(host.owner_id))


class ReturnToOwnerOnLTB(Effect):
    """Although the OnwershipMod will be removed upon LTB; need to transfer the stolen GameCard across boards"""
    listens_to = ZoneChangeEvent

    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        for c in gs.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod):
                    gs.boards[source.owner_id].remove(c)
                    gs.boards[flip(source.owner_id)].append(c)


class CitanulDruid(Effect):
    """Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or 'Artifact' not in event.card.props.card_types:
            return
        source.counters.add_counter(PLUS_ONE)


class AnkhOfMishra(Effect):
    """Whenever a land enters, this artifact deals 2 damage to that land's controller"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class DingusEgg(Effect):
    """Whenever a land is put into a graveyard from battlefield, deal 2 damage to that land's controller."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.GRAVEYARD or event.from_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class GoblinShrineOnLeave(Effect):
    """... When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.from_zone != Zone.BATTLEFIELD or event.card.props.slug != 'goblin-shrine':
            return
        for goblin in gs.card_filter.in_play().by_sub_type('Goblin').creatures().result():
            gs.apply_damage(event.card, 1, goblin)


class FieldOfDreams(Effect):
    """Players play with the top card of their libraries revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if Zone.LIBRARY not in (event.to_zone, event.from_zone):
            return
        player_idx = event.card.owner_id
        if gs.libraries[player_idx]:
            gs.libraries[player_idx][0].reveal()


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


class LandEquilibrium(Effect):
    """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
    that player instead puts that land onto the battlefield then sacrifices a land of their choice"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id == event.card.owner_id or event.card not in gs.card_filter.land().result():
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if len(opp_lands) < your_land_cnt:
            return
        gs.action_stack.push(SacChoice(event.card.owner_id, gs, source, opp_lands), gs, False)


class MoldDemonETB(Effect):
    """When this creature enters, sacrifice this creature unless you sacrifice two Swamps"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.to_zone != Zone.BATTLEFIELD:
            return
        your_swamps = gs.card_filter.on_player_board(source.owner_id).swamps().result()
        if len(your_swamps) < 2:
            gs.destroy(event.card, False)
        gs.action_stack.push(MoldDemonChoice(gs.turn_mgr.player_turn_idx, gs, source, your_swamps), gs, False)


class StanggOnLeave(Effect):
    """Exile that Stangg Twin token when Stangg leaves the battlefield; sacrific Stangg when Stangg Twin LTB"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.card.props.slug not in ('stangg', 'stangg-twin') or event.card.owner_id != source.owner_id:
            return
        if event.from_zone != Zone.BATTLEFIELD:
            return
        other_slug = 'stangg-twin' if event.card.props.slug == 'stangg' else 'stangg'
        other_card = gs.card_filter.on_player_board(event.card.owner_id).by_slug(other_slug).result()[0]
        gs.destroy(other_card)


class Kismet(Effect):
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
        gs.tap_card(event.card)
