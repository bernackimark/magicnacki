import unittest

from tests.setup_helpers import TestGame


class TestModQueries(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_blood_moon(self):
        """All non-basic lands are Mountains"""
        self.g.battlefield('blood-moon')
        basic_land = self.g.battlefield('plains')
        non_basic_land = self.g.battlefield('library-of-alexandria')
        self.assertEqual(['W'], basic_land.mana_produced)
        self.assertEqual(['R'], non_basic_land.mana_produced)
        self.assertEqual(['Mountain'], non_basic_land.card_sub_types)

    def test_crusade(self):
        """All white creatures get +1/+1"""
        white_creature = self.g.battlefield('tundra-wolves')  # 1/1
        non_white_creature = self.g.battlefield('scryb-sprites')  # 1/1
        self.assertEqual(white_creature.power, non_white_creature.power)  # 1 & 1
        card = self.g.battlefield('crusade')
        self.assertNotEqual(white_creature.power, non_white_creature.power)  # 2 & 1
        self.gs.pile_mgr.destroy(card)
        self.assertEqual(white_creature.power, non_white_creature.power)  # 1 & 1

    def test_deep_water(self):
        """{U}: Until end of turn, if you tap a land you control for mana, it produces {U} instead of any other type"""
        card = self.g.battlefield('deep-water')
        aa = card.activated_abilities[0]
        swamp = self.g.battlefield('swamp')
        self.g.activate_ability(aa)
        self.assertEqual(['U'], swamp.mana_produced)

        self.g.next_turn()
        self.assertEqual(['B'], swamp.mana_produced)

    def test_gaeas_liege_turn_land_into_forest(self):
        """{T}: Target land becomes a Forest until this creature leaves the battlefield"""
        self.g.mana('GGG')
        card = self.g.battlefield('gaeas-liege')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('mountain', owner=1)
        self.g.activate_ability(aa, target)
        self.assertEqual(['G'], target.mana_produced)
        self.assertEqual(['Forest'], target.card_sub_types)

        self.gs.pile_mgr.destroy(card)
        self.assertEqual(['R'], target.mana_produced)
        self.assertEqual(['Mountain'], target.card_sub_types)

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

    def test_sunglasses_of_urza(self):
        """You may spend white mana as though it were red mana"""
        self.g.battlefield('sunglasses-of-urza')
        plains = self.g.battlefield('plains')
        self.assertIn('R', plains.mana_produced)


if __name__ == '__main__':
    unittest.main()

