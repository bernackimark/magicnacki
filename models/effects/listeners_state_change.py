from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base import Listener
from models.events_all import StateBasedEvent
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class CityInABottle(Listener):
    """Whenever a nontoken permanent with a name originally printed in Arabian Nights is on battlefield, sac it"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        for c in gs.card_filter.in_play().non_token().result():
            if c in gs.card_filter.by_set_code('AN').result():
                gs.pile_mgr.destroy(c, allow_regeneration=False)


class GoblinsOfTheFlarg(Listener):
    """When you control a Dwarf, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        if source.props.slug != 'goblins-of-the-flarg':
            return None

        if gs.card_filter.on_player_board(source.owner_id).by_sub_type('Dwarf').result():
            gs.pile_mgr.destroy(source, allow_regeneration=False)


class JihadSac(Listener):
    """When the chosen player controls no nontoken permanents of the chosen color, sacrifice this enchantment"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        declared_color = source.extras.get('color_declaration')
        opp = flip(source.owner_id)
        if not gs.card_filter.on_player_board(opp).by_color(declared_color).non_token().permanents().result():
            gs.pile_mgr.destroy(source, allow_regeneration=False)


class SerendibDjinnNoLands(Listener):
    """When you control no lands, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            print(f'Player #{source.owner_id} has no lands, so Serendib Djinn is destroyed')
            gs.pile_mgr.destroy(source, allow_regeneration=False)
