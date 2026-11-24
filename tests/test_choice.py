import unittest

from tests.setup_helpers import TestGame

class TestCardsQRS(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs


if __name__ == '__main__':
    unittest.main()
