from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from models.events_all import DiesEvent, TapCardEvent

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.constants import COLOR_LETTERS_W_COLORLESS
from models.utils import flip
from .base import Effect

class AddMana(Effect):
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be one of: {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.mana_pools[source.owner_id].add_floating(self.color, self.cnt)

class DrainPower(Effect):
    """Target player activates a mana ability of each land they control.
    Then that player loses all unspent mana & you add the mana lost this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose available mana will be targeted & given to the other player"""
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        land_giver_mana = gs.mana_pools[target].available_mana.copy()
        for color, amt in land_giver_mana.items():
            gs.mana_pools[source.owner_id].add_floating(color, amt)

class EnergyTap(Effect):
    """Tap target untapped creature you control to add an amount of {C} equal to that creature's mana value."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            return
        gs.tap_card(target)
        gs.mana_pools[source.owner_id].add_floating('C', source.props.casting_weight)
        print(f"{source} taps to add {source.props.casting_weight} colorless to your mana pool.")

class ExchangeLifeTotals(Effect):
    def resolve(self, gs: GameState, s: GameCard, _: Optional[GameCard] = None):
        your_life = gs.score_mgr.life[s.owner_id]
        opp_life = gs.score_mgr.life[flip(s.owner_id)]
        gs.score_mgr.life[s.owner_id], gs.score_mgr.life[flip(s.owner_id)] = opp_life, your_life

class SuChi(Effect):
    """When this creature dies, add {CCCC}"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.mana_pools[source.owner_id].add_floating('C', 4)

class UrzasTrio(Effect):
    """{T}: Add {C}.
    urzas-mine: If you control an Urza's Power-Plant and an Urza's Tower, add {CC} instead.
    urzas-power-plant: If you control an Urza's Mine and an Urza's Tower, add {CC} instead.
    urzas-tower: If you control an Urza's Mine and an Urza's Power-Plant, add {CCC} instead"""
    def resolve(self, gs: GameState, s: GameCard, _: Optional[GameCard] = None):
        mines = gs.card_filter.on_player_board(s.owner_id).by_slug('urzas-mine').result()
        power_plants = gs.card_filter.on_player_board(s.owner_id).by_slug('urzas-power-plant').result()
        towers = gs.card_filter.on_player_board(s.owner_id).by_slug('urzas-tower').result()
        if not (mines and power_plants and towers):
            gs.mana_pools[s.owner_id].add_floating('C')
        elif s.props.slug == 'urzas-tower':
            gs.mana_pools[s.owner_id].add_floating('CCC')
        else:
            gs.mana_pools[s.owner_id].add_floating('CC')

class WildGrowth(Effect):
    """Enchant land Whenever enchanted land is tapped for mana, its controller adds another {G}"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if source.host is not event.card:
            return
        gs.mana_pools[event.card.owner_id].add_floating('G')
