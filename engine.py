from dataclasses import dataclass

from deck_builder.build_deck import CardUniverse, Deck, DeckBuilder, OLD_SCHOOL_DB_RULE_SET
from models.game_history import GameHistory, HistoryRecord
from game_state import GameState
from players import Player, ConsolePlayer
from renderers import Renderer, ConsoleRenderer

@dataclass
class Engine:
    players: list[Player]
    renderer: Renderer
    gs: GameState = None
    # log: Log = field(default_factory=Log)

    @property
    def player_cnt(self) -> int:
        return len(self.players)

    def play(self) -> None:
        while not self.gs.is_game_over:
            actions = self.gs.get_available_actions(self.gs.action_on_idx)
            self.renderer.render(self.gs, self.players)
            if not actions:
                continue
            action = self.players[self.gs.action_on_idx].make_move(self.gs, actions)
            action.play()
            self.gs.game_history.append(HistoryRecord(action, self.gs))


if __name__ == '__main__':
    # build decks from json file
    import json
    with open('testing/cards_for_game_testing.json', 'r') as f:
        data = json.load(f)

    universe = CardUniverse(data['universe'])
    deck_0 = data['deck_0']
    deck_1 = data['deck_1']
    if data['starting_deck'] == 1:
        deck_0, deck_1 = deck_1, deck_0

    decks = []
    for i, cards in enumerate((deck_0, deck_1)):
        deck_builder = DeckBuilder(OLD_SCHOOL_DB_RULE_SET, i)
        for card_slug, qty in cards:
            for _ in range(qty):
                deck_builder.add_card_by_slug(card_slug)
        deck: Deck = deck_builder.complete_deck()
        decks.append(deck)

    # for speed of testing, reduce all cards' casting costs
    for d in decks:
        for c in d.cards:
            if not c.casting_cost:
                continue
            if c.casting_cost[-1] not in ('B', 'U', 'G', 'R', 'W'):
                c.casting_cost = '1'
            else:
                c.casting_cost = c.casting_cost[-1] if 'X' not in c.casting_cost else f'X{c.casting_cost[-1]}'

    # create players
    players = [ConsolePlayer(0, 'Mark', False), ConsolePlayer(1, 'Bull', False)]

    # create engine
    e = Engine(players=players, renderer=ConsoleRenderer(),
               gs=GameState(len(players), 0, decks=decks))
    e.play()


