import unittest

from models.effects.resolvers_a_to_e import BloodLust
from tests.setup_helpers import create_engine_and_universe, get_card, add_to_battlefield


class TestCardsAtoC(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_blood_lust(self):
        """If target creature has toughness 5 or greater, it gets +4/-4 until end of turn.
        Otherwise, it gets +4/-X until end of turn, where X is its toughness minus 1."""
        large_creature = get_card(self.gs, 'bartel-runeaxe', 0)  # 6/5
        small_creature = get_card(self.gs, 'merfolk-of-the-pearl-trident', 0)  # 1/1
        blood_lust = get_card(self.gs, 'blood-lust', 1)
        add_to_battlefield(large_creature, self.gs)
        add_to_battlefield(small_creature, self.gs)
        BloodLust().resolve(self.gs, blood_lust, large_creature)
        BloodLust().resolve(self.gs, blood_lust, small_creature)
        self.assertEqual(large_creature.power, 10)
        self.assertEqual(large_creature.toughness, 1)
        self.assertEqual(small_creature.power, 5)
        self.assertEqual(small_creature.toughness, 1)

    # def test_creature_bond(self):
    #     """When host dies, this Aura deals damage equal to that creature's toughness to the creature's controller."""
    #     # TODO: By the time CreatureBond.on_event() is called, the source.host is None;
    #     #  I'm guessing the aura is detached already
    #     host = get_card(self.gs, 'merfolk-of-the-pearl-trident', 0)  # 1/1
    #     creature_bond = get_card(self.gs, 'creature-bond', 1)
    #     host.auras.append(creature_bond)
    #     self.gs.event_mgr.register(creature_bond.abilities[0].effect, creature_bond)
    #     self.gs.pile_mgr.destroy(host)
    #     self.assertEqual(self.gs.score_mgr.life[0], 19)


if __name__ == '__main__':
    unittest.main()

