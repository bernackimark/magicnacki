import unittest

from .setup_helpers import create_engine_and_universe


class TestCombat(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe('testing/game_testing_settings.json',
                                                                'engine_testing_setup_a', True)
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs


if __name__ == '__main__':
    unittest.main()
