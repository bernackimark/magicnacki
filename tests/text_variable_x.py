import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import SelectXAction2
from models.actions.stack_accept_counter import AcceptAction
from tests.setup_helpers import TestGame


class TestVariableX(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_x_cast_simple(self):
        """Verify casting pipeline flow for X spells:
        - choose X
        - choose target
        - resolve ability"""
        card = self.g.card('stream-of-life')
        self.g.mana('GGGG')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])

        # Pipeline should request X selection
        pipeline.advance()
        self.assertIsNotNone(self.gs.pending_choice)

        # Player chooses X=3
        SelectXAction2(0, self.gs, pipeline, 3).play()

        # Pipeline should now request target selection
        pipeline.advance()
        self.assertIsNotNone(self.gs.pending_choice)

        # Choose player 0 as target
        target_actions = self.gs.pending_choice.get_actions()
        target_action = next(a for a in target_actions if a.target == 0)
        target_action.play()

        # Pipeline should now be complete
        pipeline.advance()

        # Accept the generated AbilityAction
        AcceptAction(1, self.gs).play()
        self.assertEqual(self.gs.score_mgr.life[0], 23)

    def test_x_activation_simple(self):
        """Verify activation pipeline flow for X abilities:
        - choose X
        - choose target
        - resolve ability"""
        card = self.g.battlefield('banshee')
        self.g.mana('WWW')

        self.g.next_turn()
        aa = card.activated_abilities[0]
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)

        # Pipeline should request X selection
        pipeline.advance()
        self.assertIsNotNone(self.gs.pending_choice)

        # Player chooses X=3
        SelectXAction2(0, self.gs, pipeline, 3).play()

        # Pipeline should now request target selection
        pipeline.advance()
        self.assertIsNotNone(self.gs.pending_choice)

        # Choose player 1 as target
        target_actions = self.gs.pending_choice.get_actions()
        target_action = next(a for a in target_actions if a.target == 1)
        target_action.play()

        # Pipeline should now be complete
        pipeline.advance()

        # Accept the generated AbilityAction
        AcceptAction(1, self.gs).play()

        self.assertEqual([18, 19], [self.gs.score_mgr.life[0], self.gs.score_mgr.life[1]])

    def test_xx(self):
        card = self.g.hand('part-water')  # casting_cost: XXU
        self.g.mana('UUUU')
        eff_spec = card.abilities[0]
        pipeline = AbilityPipeline(0, self.gs, card, eff_spec)

        # Pipeline should request X selection
        pipeline.advance()

        # since XX must draw from the remaining UUU, only X=1 is allowed
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))


if __name__ == '__main__':
    unittest.main()
