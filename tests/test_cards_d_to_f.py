import unittest

from models.actions.activate_ability import ActivateAbility
from models.actions.special import Attach
from models.effects.listeners_misc import ArtifactPossessionActivation
from models.effects.resolvers_a_to_e import BloodLust
from models.events_all import AbilityActivatedEvent
from tests.setup_helpers import TestGame


class TestCardsAtoC(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_fellwar_stone_1(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('plains', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))

    def test_fellwar_stone_2(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('birds-of-paradise', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))


if __name__ == '__main__':
    unittest.main()

