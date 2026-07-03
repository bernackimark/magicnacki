import unittest

from tests.setup_helpers import TestGame


class TestCardsWtoZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_wheel_of_fortune(self):
        """Each player discards their hand, then draws seven cards"""
        original_card_ids = {c.id_ for c in list(self.gs.pile_mgr.hands[0].cards)}
        wheel_of_fortune = self.g.card('wheel-of-fortune')
        self.g.mana('RRRR')
        wheel_of_fortune.abilities[0].effect.resolve(self.gs, wheel_of_fortune, None)
        current_card_ids = {c.id_ for c in self.gs.pile_mgr.hands[0].cards}
        self.assertTrue(original_card_ids.isdisjoint(current_card_ids))


if __name__ == '__main__':
    unittest.main()

