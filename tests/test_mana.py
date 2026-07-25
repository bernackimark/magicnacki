import unittest

from models.systems.mana import ManaCost
from tests.setup_helpers import TestGame


class TestMana(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_mana_taps_after_use(self):
        plains = self.g.battlefield('plains')
        self.g.battlefield('savannah-lions', pay_mana=True)
        self.assertTrue(plains.is_tapped)
        self.assertEqual(0, sum(self.gs.mana_pools[0].available_mana.values()))

class ManaCostMath(unittest.TestCase):
    def test_adding_two_costs(self):
        a = ManaCost('2GB')
        b = ManaCost('1BU')
        self.assertEqual('3BBUG', a + b)

    def test_subtracting_two_costs(self):
        a = ManaCost('3B')
        b = ManaCost('5GG')
        self.assertEqual('B', a - b)


if __name__ == '__main__':
    unittest.main()
