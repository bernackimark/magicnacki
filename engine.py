from dataclasses import dataclass

from build_deck import CardUniverse, Deck, DeckBuilder
from game_state import GameState, Action
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
            self.gs.game_history.append((self.gs.turn_number, action))


# build decks
universe = CardUniverse(['1E', '3E', '4E', 'DK'])
his_cards = (('plains', 24), ('tundra-wolves', 4), ('savannah-lions', 4),
             ('disenchant', 4), ('blessing', 4))
my_cards = (('island', 32), ('merfolk-of-the-pearl-trident', 4), ('lord-of-atlantis', 4), ('apprentice-wizard', 4),
            ('air-elemental', 4))

decks = []
for i, cards in enumerate((my_cards, his_cards)):
    deck_builder = DeckBuilder(universe, i)
    for card_slug, qty in cards:
        for _ in range(qty):
            deck_builder.add_card_by_slug(card_slug)
    deck: Deck = deck_builder.complete_deck()
    decks.append(deck)

# create players
players = [ConsolePlayer(0, 'Mark', False), ConsolePlayer(1, 'Bull', False)]

# create engine
e = Engine(players=players,
           renderer=ConsoleRenderer(),
           gs=GameState(len(players), 0, decks=decks))
e.play()


