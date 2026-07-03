import unittest

from models.actions.activate_ability import ActivateAbility
from models.actions.cast import CastToBoard
from models.actions.draw_discard import DrawCard
from models.actions.end_step_pass_turn import PassTheTurn
from models.effects.base import Spell
from models.effects.resolvers_generic import TakeAnotherTurn
from models.effects.resolvers_p_to_z import Timetwister
from models.events_all import CastResolvedEvent
from tests.setup_helpers import TestGame


class TestCardsWtoZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_time_vault(self):
        """This artifact enters tapped. This artifact doesn't untap during your untap step.
        If you would begin your turn while this artifact is tapped, you may: skip that turn & untap this artifact.
        {T}: Take an extra turn after this one."""
        self.g.mana('UUUUUUUUUU')
        tv = self.g.battlefield('time-vault')
        self.assertTrue(tv.is_tapped)
        PassTheTurn(0, self.gs).play()
        PassTheTurn(1, self.gs).play()
        skip_turn_and_untap_tv = self.gs.pending_choice.options[0]
        skip_turn_and_untap_tv.play()
        ActivateAbility(0, self.gs, tv.activated_abilities[0]).play()
        PassTheTurn(0, self.gs).play()
        self.assertEqual(0, self.gs.turn_mgr.player_turn_idx)
        self.assertTrue(tv.is_tapped)

    def test_verduran_enchantress(self):
        """Whenever you cast an enchantment spell, you may draw a card"""
        self.g.battlefield('verduran-enchantress')
        self.g.mana('UUUUU')
        enchantment = self.g.card('undertow')
        cast_event = CastResolvedEvent(enchantment, 0)
        self.gs.event_mgr.emit(cast_event, self.gs)
        self.assertTrue(any(isinstance(a, DrawCard) for a in self.gs.pending_choice.options))


class TestTimetwisterSeparately(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_timetwister(self):
        """Each player shuffles their hand & graveyard into their library, then draws seven cards.
        (Then put Timetwister into its owner's graveyard.)"""
        # This has been failing if there are other tests in this class
        self.g.graveyard('scryb-sprites')
        self.g.graveyard('serra-angel')
        self.g.hand('island')
        self.g.hand('island')
        tt = self.g.graveyard('timetwister')
        Timetwister().resolve(self.gs, tt, None)
        self.assertTrue(7, len(self.gs.pile_mgr.hands[0].cards))
        self.assertIn(tt, self.gs.pile_mgr.graveyards[0])


if __name__ == '__main__':
    unittest.main()
