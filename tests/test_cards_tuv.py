import unittest

from models.actions.draw_discard import DrawCard
from models.events_all import CastResolvedEvent
from tests.setup_helpers import TestGame


class TestCardsWtoZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_verduran_enchantress(self):
        """Whenever you cast an enchantment spell, you may draw a card"""
        self.g.battlefield('verduran-enchantress')
        self.g.mana('UUUUU')
        enchantment = self.g.card('undertow')
        cast_event = CastResolvedEvent(enchantment, 0)
        self.gs.event_mgr.emit(cast_event, self.gs)
        self.assertTrue(any(isinstance(a, DrawCard) for a in self.gs.pending_choice.options))


if __name__ == '__main__':
    unittest.main()
