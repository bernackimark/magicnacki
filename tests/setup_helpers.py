from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

from data.user_data import get_user
from engine import Engine, deflate_costs
from models.constants import Mulligan
from models.game_card.card import CardUniverse
from models.game_card.game_card import GameCard
from models.deck import Deck
from models.match_manager import MatchManager
from players import ConsolePlayer
from renderers import ConsoleRenderer


def create_engine_and_universe(file_path_str: str, settings_key: str, test_mode: bool = True) -> tuple[Engine, CardUniverse]:
    """From provided path string & key, pull JSON; create CardUniverse; create decks;
    deflate casting costs, if applicable; set rules; create & return a fresh Engine oboject
    """
    import json
    with open(file_path_str, 'r') as f:
        data = json.load(f)
        data = data[settings_key]

    universe = CardUniverse(data['universe'])

    decks = [Deck.from_json(deck_id, str(i)) for i, deck_id in enumerate((data['deck_0'], data['deck_1']))]

    # if deflate_c_costs:
    #     deflate_casting_costs(decks)

    # create players
    players = []
    for i, user_id in enumerate(data['users']):
        user_data = get_user(user_id)
        player = ConsolePlayer(i, user_data.handle, user_data.is_bot)
        players.append(player)

    # would put in the testing JSON, but not sure how to convert mulligan to enum member
    rules = {'mulligan': Mulligan.LONDON_WITH_GENTLEMENS, 'best_of': 3}

    eng = Engine(players=players, renderer=ConsoleRenderer(),
                 match_manager=MatchManager(len(players), rules, decks, universe.token_cards,
                                            first_to_act=data['starting_deck']))
    if test_mode:
        deflate_costs(eng.match_manager.deck_game_cards)
    return eng, universe

def get_card(gs: GameState, slug: str, player_id: int = 0) -> GameCard:
    cu = CardUniverse(["lea", "leb", "2ed", "arn", "atq", "3ed", "leg", "drk"])
    game_card = GameCard(cu[slug], player_id)
    game_card.game_state = gs
    return game_card

def add_to_battlefield(card: GameCard, gs: GameState):
    gs.pile_mgr.boards[card.owner_id].append(card)

def put_onto_battlefield_this_turn(card: GameCard, gs: GameState):
    gs.pile_mgr.boards[card.owner_id].append(card)
    card.turn_entered_under_current_controller = gs.turn_mgr.turn_number

def put_onto_battlefield_last_turn(card: GameCard, gs: GameState):
    gs.pile_mgr.boards[card.owner_id].append(card)
    gs.turn_mgr.most_recent_turn_started[card.owner_id] += 1
    card.turn_entered_for_owner = gs.turn_mgr.most_recent_turn_started[card.owner_id] - 1
