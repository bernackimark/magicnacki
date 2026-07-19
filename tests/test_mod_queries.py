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

    def test_giant_tortoise(self):
        """This creature gets +0/+3 as long as it's untapped"""
        card = self.g.battlefield('giant-tortoise')  # 1/1
        self.assertEqual(4, card.toughness)
        card.tap()
        self.assertEqual(1, card.toughness)

    def test_nightmare(self):
        """Nightmare's power and toughness are each equal to the number of Swamps you control"""
        self.g.mana('BB')
        card = self.g.battlefield('nightmare')
        self.assertEqual(2, card.toughness)
        swamp = self.g.battlefield('swamp')
        self.assertEqual(3, card.power)
        self.gs.pile_mgr.destroy(swamp)
        self.assertEqual(2, card.power)

    def test_plague_rats(self):
        """PR's power & toughness are each equal to the number of creatures named Plague Rats on the battlefield"""
        card = self.g.battlefield('plague-rats')
        self.assertEqual(1, card.toughness)
        pr_2 = self.g.battlefield('plague-rats')
        self.assertEqual(2, card.toughness)
        self.gs.pile_mgr.destroy(pr_2)
        self.assertEqual(1, card.toughness)


if __name__ == '__main__':
    unittest.main()

