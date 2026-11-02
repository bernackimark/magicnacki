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

    def test_can_pay_basic(self):
        mp = self.gs.mana_pools[0]
        self.g.mana('WWG')
        self.assertFalse(mp.can_pay('GG'))
        self.assertFalse(mp.can_pay('WWW'))
        self.assertFalse(mp.can_pay('4'))
        self.assertTrue(mp.can_pay('WG'))
        self.assertTrue(mp.can_pay('WW'))
        self.assertTrue(mp.can_pay('W'))
        self.assertTrue(mp.can_pay('2'))
        self.assertTrue(mp.can_pay(''))

    def test_can_pay_x(self):
        mp = self.gs.mana_pools[0]
        self.g.mana('WWG')
        self.assertFalse(mp.can_pay('XW', x_value=3))
        self.assertFalse(mp.can_pay('XWG', x_value=2))
        self.assertTrue(mp.can_pay('XW', x_value=2))
        self.assertTrue(mp.can_pay('XWG', x_value=1))
        self.assertTrue(mp.can_pay('XWWG', x_value=0))
        self.assertTrue(mp.can_pay('X2', x_value=1))

    def test_can_pay_xx(self):
        mp = self.gs.mana_pools[0]
        self.g.mana('WWG')
        self.assertFalse(mp.can_pay('XXW', x_value=2))
        self.assertFalse(mp.can_pay('XX', x_value=2))
        self.assertTrue(mp.can_pay('XXG', x_value=1))
        self.assertTrue(mp.can_pay('XXWWG', x_value=0))

    def test_get_max_x(self):
        mp = self.gs.mana_pools[0]
        self.g.mana('WWG')
        self.assertEqual(0, mp.get_max_x('XWWG'))
        self.assertEqual(1, mp.get_max_x('XWG'))
        self.assertEqual(2, mp.get_max_x('XW'))
        self.assertEqual(1, mp.get_max_x('XXW'))

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
