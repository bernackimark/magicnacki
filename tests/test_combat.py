import unittest

from models.modifiers import KWAMod
from tests.setup_helpers import TestGame


class TestCombat(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_create_combat_adds_attacker(self):
        attacker = self.g.card('grizzly-bears')
        self.gs.combat_mgr.create_combat(attacker)
        self.assertEqual([attacker], self.gs.combat_mgr.attackers)
        self.assertIs(self.gs.combat_mgr.get_combat(attacker).attacker, attacker)

    def test_get_combatants_against(self):
        attacker = self.g.card('grizzly-bears')
        blocker = self.g.card('hill-giant', 1)
        self.gs.combat_mgr.create_combat(attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        self.assertEqual([blocker], self.gs.combat_mgr.get_combatants_against(attacker))
        self.assertEqual([attacker], self.gs.combat_mgr.get_combatants_against(blocker))

    def test_blocked_combat_assigns_damage(self):
        attacker = self.g.battlefield('grizzly-bears')  # 2/2
        blocker = self.g.battlefield('hill-giant', owner=1)  # 3/3
        self.g.combat(attacker, blocker)
        self.assertEqual(attacker.damage_received_this_turn, blocker.power)
        self.assertEqual(blocker.damage_received_this_turn, attacker.power)

    def test_trample_assigns_excess_damage_to_player(self):
        attacker = self.g.battlefield('craw-wurm')  # 6/4
        blocker = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)  # 1/1
        attacker.modifiers.append(KWAMod(s=attacker, add_or_remove='add', kwa='Trample'))
        self.g.combat(attacker, blocker)
        expected_trample = attacker.power - blocker.toughness
        self.assertEqual(20 - expected_trample, self.gs.life[1])

    def test_remove_blocker_from_combat(self):
        """Blocker should be removed from battlefield, but attacker should deal no damage (except for trample)"""
        attacker = self.g.card('grizzly-bears')
        blocker = self.g.card('hill-giant', 1)
        unsummon = self.g.card('unsummon', 1)
        self.g.mana('U', 1)
        self.gs.combat_mgr.create_combat(attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        self.gs.combat_mgr.remove_from_combat(blocker)
        self.g.cast_and_accept(unsummon, blocker, unsummon.abilities[0], owner=1)
        self.assertNotIn(blocker, self.gs.card_filter.in_play().result())
        combat.handle_damage()
        self.assertEqual(self.gs.life[1], 20)

    def test_remove_attacker_from_combat(self):
        attacker = self.g.card('grizzly-bears')
        attacker.tap()
        self.gs.combat_mgr.create_combat(attacker)
        self.gs.combat_mgr.remove_from_combat(attacker)
        self.assertEqual([], self.gs.combat_mgr.combats)
        self.assertFalse(attacker.is_tapped)

    def test_get_combat_returns_none_when_card_not_in_combat(self):
        creature = self.g.card('grizzly-bears')
        self.assertIsNone(self.gs.combat_mgr.get_combat(creature))

    def test_first_strike_attacker(self):
        attacker = self.g.battlefield('tundra-wolves')
        blocker = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        self.g.combat(attacker, blocker)
        self.assertIn(blocker, self.g.gy[1])
        self.assertNotIn(attacker, self.g.gy[0])

    def test_first_strike_blocker(self):
        attacker = self.g.battlefield('merfolk-of-the-pearl-trident')
        blocker = self.g.battlefield('tundra-wolves', owner=1)
        self.g.combat(attacker, blocker)
        self.assertIn(attacker, self.g.gy[0])
        self.assertNotIn(blocker, self.g.gy[1])

    def test_first_strike_only_deals_damage_once(self):
        attacker = self.g.battlefield('white-knight')  # 2/2 First Strike
        blocker = self.g.battlefield('phantom-monster', owner=1)  # 3/3
        self.g.combat(attacker, blocker)
        self.assertIn(blocker, self.gs.pile_mgr.boards[1], 'First Striker appears to have dealt damage 2x')

    def test_unblocked_attacker_damage(self):
        attacker = self.g.battlefield('white-knight')  # 2/2 First Strike
        self.g.combat(attacker, None)
        self.assertEqual(18, self.gs.life[1])


if __name__ == '__main__':
    unittest.main()
