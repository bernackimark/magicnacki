import unittest

from models.actions.end_step_pass_turn import PassTheTurn
from models.phase_manager import Phase
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

    def test_whirlish_dervish(self):
        """At each end step, if WD dealt damage to an opponent this turn, put a +1/+1 counter on it."""
        wd = self.g.battlefield('whirling-dervish')
        PassTheTurn(0, self.gs).play()
        PassTheTurn(1, self.gs).play()
        self.gs.combat_mgr.create_combat(self.gs, wd)
        combat = self.gs.combat_mgr.get_combat(wd)
        combat.handle_damage()
        self.gs.phase_mgr.set_phase(Phase.END_STEP, self.gs)
        self.assertEqual(2, wd.power)


if __name__ == '__main__':
    unittest.main()

