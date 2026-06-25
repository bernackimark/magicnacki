import unittest

from models.actions.cast import CastToTargetAddToStack
from models.actions.stack_accept_counter import AcceptAction
from models.modifiers import KWAMod
from tests.setup_helpers import create_engine_and_universe, get_card, add_to_battlefield


class TestCombat(unittest.TestCase):
    def setUp(self):
        self.engine, self.universe = create_engine_and_universe()
        self.engine.gs = self.engine.match_manager.create_game_state()
        self.gs = self.engine.gs

    def test_create_combat_adds_attacker(self):
        attacker = get_card(self.gs, 'grizzly-bears', 0)
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        self.assertEqual([attacker], self.gs.combat_mgr.attackers)
        self.assertIs(self.gs.combat_mgr.get_combat(attacker).attacker, attacker)

    def test_get_combatants_against(self):
        attacker = get_card(self.gs, 'grizzly-bears', 0)
        blocker = get_card(self.gs, 'hill-giant', 1)
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        self.assertEqual([blocker], self.gs.combat_mgr.get_combatants_against(attacker))
        self.assertEqual([attacker], self.gs.combat_mgr.get_combatants_against(blocker))

    def test_blocked_combat_assigns_damage(self):
        attacker = get_card(self.gs, 'grizzly-bears', 0)  # 2/2
        blocker = get_card(self.gs, 'hill-giant', 1)  # 3/3
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        combat.handle_damage()
        self.assertEqual(attacker.damage_received_this_turn, blocker.power)
        self.assertEqual(blocker.damage_received_this_turn, attacker.power)

    def test_trample_assigns_excess_damage_to_player(self):
        attacker = get_card(self.gs, 'craw-wurm', 0)  # 6/4
        blocker = get_card(self.gs, 'merfolk-of-the-pearl-trident', 1)  # 1/1
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        attacker.modifiers.append(KWAMod(s=attacker, add_or_remove='add', kwa='Trample'))
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        starting_life = self.gs.score_mgr.life[1]
        combat.handle_damage()
        expected_trample = attacker.power - blocker.toughness
        self.assertEqual(starting_life - expected_trample, self.gs.score_mgr.life[1])

    def test_remove_blocker_from_combat(self):
        """Blocker should be removed from battlefield, but attacker should deal no damage (except for trample)"""
        attacker = get_card(self.gs, 'grizzly-bears', 0)
        blocker = get_card(self.gs, 'hill-giant', 1)
        unsummon = get_card(self.gs, 'unsummon', 1)
        island = get_card(self.gs, 'island', 1)
        add_to_battlefield(island, self.gs)
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        self.gs.combat_mgr.remove_from_combat(blocker)
        CastToTargetAddToStack(1, self.gs, unsummon, blocker, unsummon.abilities[0]).play()
        AcceptAction(0, self.gs).play()
        self.assertNotIn(blocker, self.gs.card_filter.in_play().result())
        combat.handle_damage()
        self.assertEqual(self.gs.score_mgr.life[1], 20)

    def test_remove_attacker_from_combat(self):
        attacker = get_card(self.gs, 'grizzly-bears', 0)
        attacker.tap()
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        self.gs.combat_mgr.remove_from_combat(attacker)
        self.assertEqual([], self.gs.combat_mgr.combats)
        self.assertFalse(attacker.is_tapped)

    def test_get_combat_returns_none_when_card_not_in_combat(self):
        creature = get_card(self.gs, 'grizzly-bears', 0)
        self.assertIsNone(self.gs.combat_mgr.get_combat(creature))

    def test_first_strike_only_deals_damage_once(self):
        attacker = get_card(self.gs, 'white-knight', 0)  # 2/2 First Strike
        blocker = get_card(self.gs, 'phantom-monster', 1)  # 3/3
        add_to_battlefield(attacker, self.gs)
        add_to_battlefield(blocker, self.gs)
        self.gs.combat_mgr.create_combat(self.gs, attacker)
        combat = self.gs.combat_mgr.get_combat(attacker)
        combat.blockers.append(blocker)
        combat.handle_damage()
        self.assertIn(blocker, self.gs.pile_mgr.boards[1], 'First Striker appears to have dealt damage 2x')


if __name__ == '__main__':
    unittest.main()
