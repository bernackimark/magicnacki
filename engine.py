from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard

from data.user_data import get_user
from models.deck import CardUniverse, Deck
from game_state import GameState
from models.constants import Mulligan
from models.match_manager import MatchManager
from players import Player, ConsolePlayer
from renderers import Renderer, ConsoleRenderer

@dataclass
class Engine:
    players: list[Player]
    renderer: Renderer
    match_manager: MatchManager
    gs: GameState = None
    # log: Log = field(default_factory=Log)

    @property
    def player_cnt(self) -> int:
        return len(self.players)

    def play(self) -> None:
        """Controls game flow, user inputs & rendering;
        creates GameState if not passed in; double loop for match & game, creating a new GameState in between"""
        if self.gs is None:
            self.gs = self.match_manager.create_game_state()
        while not self.match_manager.is_match_over:
            while not self.gs.is_game_over:
                actions = self.gs.get_available_actions(self.gs.action_on_idx)
                self.renderer.render(self.gs, self.players)
                if not actions:
                    continue
                action = self.players[self.gs.action_on_idx].make_move(self.gs, actions)
                action.play()
                self.gs.game_history.append_action(action, self.gs)
            self.match_manager.create_game_state()

def deflate_costs(game_card_decks: list[list[GameCard]]) -> None:
    """For speed of testing, reduce all cards' casting & activated ability costs"""
    def _deflate(cost: str):
        if cost[-1] not in ('B', 'U', 'G', 'R', 'W'):
            return '1'
        return cost[-1] if 'X' not in cost else f'X{cost[-1]}'

    for d in game_card_decks:
        for c in d:
            if c.casting_cost:
                c.casting_cost = _deflate(c.casting_cost)
            for aa in c.activated_abilities:
                if aa.eff_spec.cost:
                    aa.eff_spec.cost = _deflate(aa.eff_spec.cost)

def create_engine_from_json(file_path_str: str, settings_key: str, test_mode: bool = False) -> Engine:
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
    return eng


if __name__ == '__main__':
    e = create_engine_from_json('testing/game_testing_settings.json', 'engine_testing_setup_a', True)
    e.play()
