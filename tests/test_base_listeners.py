import unittest

from models.events_all import StateBasedEvent
from tests.setup_helpers import TestGame


class TestBaseListeners(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_zero_life(self):
        self.assertFalse(self.gs.is_game_over)
        for _ in range(7):
            card = self.g.hand('lightning-bolt')
            self.g.cast_and_accept(card, 1, card.abilities[0])
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertTrue(self.gs.is_game_over)

    def test_ten_poison(self):
        self.gs.score_mgr.add_poison_counter(1, 9)
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertFalse(self.gs.is_game_over)

        self.gs.score_mgr.add_poison_counter(1, 1)
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertTrue(self.gs.is_game_over)

    def test_islandhome(self):
        island = self.g.battlefield('island')
        card = self.g.battlefield('sea-serpent')
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertIn(card, self.gs.boards[0])

        self.gs.pile_mgr.destroy(island)
        self.gs.event_mgr.emit(StateBasedEvent())
        # self.assertIn(card, self.gs.graveyards[0])


if __name__ == '__main__':
    unittest.main()
