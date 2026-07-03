import unittest

from models.actions.draw_discard import DrawCard
from models.effects.resolvers_p_to_z import Timetwister
from models.events_all import CastResolvedEvent
from tests.setup_helpers import TestGame


class TestCardsWtoZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_timetwister(self):
        """Each player shuffles their hand & graveyard into their library, then draws seven cards.
        (Then put Timetwister into its owner's graveyard.)"""
        self.g.graveyard('scryb-sprites')
        self.g.graveyard('serra-angel')
        self.g.hand('island')
        self.g.hand('island')
        tt = self.g.graveyard('timetwister')
        Timetwister().resolve(self.gs, tt, None)
        self.assertTrue(7, len(self.gs.pile_mgr.hands[0].cards))
        self.assertIn(tt, self.gs.pile_mgr.graveyards[0])

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
