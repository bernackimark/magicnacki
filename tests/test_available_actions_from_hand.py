import unittest

from models.actions.cast import BeginSpellCastAction
from tests.setup_helpers import TestGame


class TestAvailableActionsFromHand(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_can_cast_aura_with_valid_target(self):
        self.g.battlefield('plains', 'savannah-lions')
        self.g.battlefield('savannah-lions')
        self.g.hand('holy-strength')
        self.assertIn('Cast Holy Strength', [a.__repr__() for a in self.gs.available_actions_from_hand()])

    def test_can_cast_aura_to_multiple_valid_targets(self):
        self.g.battlefield('plains', 'savannah-lions', 'tundra-wolves')
        aura = self.g.hand('holy-strength')
        BeginSpellCastAction(0, self.gs, aura, eff_spec=aura.abilities[0]).play()
        target_cnt = len(self.gs.pending_choice.get_actions())
        self.assertEqual(target_cnt, 2)

    def test_cannot_cast_auras_without_valid_target(self):
        self.g.battlefield('plains')
        self.g.hand('holy-strength')
        self.assertNotIn('Cast Holy Strength', [a.__repr__() for a in self.gs.available_actions_from_hand()])


if __name__ == '__main__':
    unittest.main()
