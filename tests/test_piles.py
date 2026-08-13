import unittest

from models.constants import Zone
from tests.setup_helpers import TestGame


class TestPileManager(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_destroy(self):
        card = self.g.battlefield("grizzly-bears")
        self.gs.pile_mgr.destroy(card)
        self.assertEqual(card.zone, Zone.GRAVEYARD)
        self.assertIn(card, self.g.gy[0])
        self.assertNotIn(card, self.gs.pile_mgr.boards[0])

    def test_exile(self):
        card = self.g.battlefield("grizzly-bears")
        self.gs.pile_mgr.exile(card)
        self.assertEqual(card.zone, Zone.EXILE)
        self.assertIn(card, self.gs.pile_mgr.exiles[0])
        self.assertNotIn(card, self.gs.pile_mgr.boards[0])

    def test_bounce(self):
        card = self.g.battlefield("grizzly-bears")
        self.gs.pile_mgr.bounce(card)
        self.assertEqual(card.zone, Zone.HAND)
        self.assertIn(card, self.gs.pile_mgr.hands[0])
        self.assertNotIn(card, self.gs.pile_mgr.boards[0])

    def test_discard(self):
        card = self.g.hand("grizzly-bears")
        self.gs.pile_mgr.discard(card)
        self.assertEqual(card.zone, Zone.GRAVEYARD)
        self.assertIn(card, self.g.gy[0])
        self.assertNotIn(card, self.gs.pile_mgr.hands[0])

    def test_reanimate(self):
        card = self.g.graveyard("grizzly-bears")
        self.gs.pile_mgr.reanimate(card)
        self.assertEqual(card.zone, Zone.BATTLEFIELD)
        self.assertIn(card, self.gs.pile_mgr.boards[0])
        self.assertNotIn(card, self.g.gy[0])

    def test_cast(self):
        card = self.g.hand("grizzly-bears")
        self.gs.pile_mgr.cast(card)
        self.assertEqual(card.zone, Zone.BATTLEFIELD)
        self.assertIn(card, self.gs.pile_mgr.boards[0])
        self.assertNotIn(card, self.gs.pile_mgr.hands[0])

    def test_draw(self):
        card = self.g.library("grizzly-bears")
        self.gs.pile_mgr.draw(0)
        self.assertEqual(card.zone, Zone.HAND)
        self.assertIn(card, self.gs.pile_mgr.hands[0])
        self.assertNotIn(card, self.gs.pile_mgr.libraries[0])


if __name__ == '__main__':
    unittest.main()
