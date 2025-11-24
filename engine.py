from dataclasses import dataclass

from build_deck import CardUniverse, Deck, DeckBuilder
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
            self.renderer.render(self.gs, self.players)
            if self.gs.get_available_actions(self.gs.action_on_idx):
                action = self.players[self.gs.action_on_idx].make_move(self.gs)
                action.play()
                self.gs.game_history.append((self.gs.turn_number, action))


# build decks
universe = CardUniverse(['3E', '4E'])
my_cards = (('plains', 24), ('tundra-wolves', 4), ('wall-of-swords', 4), ('animate-wall', 4),
            ('disenchant', 4))
his_cards = (('island', 32), ('pirate-ship', 4),  # ('merfolk-of-the-pearl-trident', 4),
             ('sea-serpent', 4)  # ('psionic-entity', 4), ('flight', 4), ('flood', 4))
            )

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


