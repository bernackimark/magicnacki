import unittest

from models.actions.cast import BeginSpellCastAction, CastToTargetAddToStack
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.special import SelectXAction
from models.actions.stack_accept_counter import AcceptAction
from models.choice_actions_all import XValueChoice
from tests.setup_helpers import TestGame


class TestVariableX(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_x_cast_simple(self):
        card = self.g.card('stream-of-life')
        self.g.mana('GGGG')
        eff_spec = card.abilities[0]
        choice = XValueChoice(0, self.gs, card, [1, 2, 3], eff_spec)  # create choices for user
        SelectXAction(0, self.gs, choice, 3).play()  # select a value of 3, assign 3 to card.extras['x']
        CastToTargetAddToStack(0, self.gs, card, 0, eff_spec).play()  # add spell to stack
        AcceptAction(1, self.gs).play()  # opponent accepts spell; spell materializes, adding 3 life
        self.assertEqual(self.gs.score_mgr.life[0], 23)

    def test_x_activation_simple(self):
        """{XT}: Banshee deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""
        card = self.g.card('banshee')
        self.g.mana('WWW')
        PassTheTurn(0, self.gs).play()  # clears summoning sickness
        PassTheTurn(1, self.gs).play()
        eff_spec = card.abilities[0]
        aa = card.activated_abilities[0]
        choice = XValueChoice(0, self.gs, card, [1, 2, 3], eff_spec, aa)  # create choices for user
        SelectXAction(0, self.gs, choice, 3).play()  # select a value of 3, assign 3 to card.extras['x']
        self.g.activate_ability(aa, 1)
        self.assertEqual((self.gs.score_mgr.life[0], self.gs.score_mgr.life[1]), (18, 19))

    def test_xx(self):
        card = self.g.hand('part-water')  # casting_cost: XXU
        self.g.mana('UUUU')
        eff_spec = card.abilities[0]
        BeginSpellCastAction(0, self.gs, card, eff_spec).play()
        self.assertEqual(len(self.gs.pending_choice.get_actions()), 1)


if __name__ == '__main__':
    unittest.main()
