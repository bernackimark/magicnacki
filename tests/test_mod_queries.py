import unittest

from tests.setup_helpers import TestGame


class TestModQueries(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_crusade(self):
        """All white creatures get +1/+1"""
        white_creature = self.g.battlefield('tundra-wolves')  # 1/1
        non_white_creature = self.g.battlefield('scryb-sprites')  # 1/1
        self.assertEqual(white_creature.power, non_white_creature.power)  # 1 & 1
        card = self.g.battlefield('crusade')
        self.assertNotEqual(white_creature.power, non_white_creature.power)  # 2 & 1
        self.gs.pile_mgr.destroy(card)
        self.assertEqual(white_creature.power, non_white_creature.power)  # 1 & 1


if __name__ == '__main__':
    unittest.main()

