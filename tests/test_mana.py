import unittest

from models.mana import ManaCost


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
