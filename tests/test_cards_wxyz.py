import unittest

from models.constants import KW, Zone
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCardsWXYZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_wall_of_vapor(self):
        """Prevent all damage that would be dealt to this creature by creatures it's blocking"""
        card = self.g.battlefield('wall-of-vapor')  # 0/1
        attacker = self.g.battlefield('craw-wurm', owner=1)  #6/4

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        com = self.gs.combat_mgr.get_combat(attacker)
        com.add_blocker(card)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertNotIn(card, self.g.gy[0])

    def test_wand_of_ith(self):
        """3T: Opponent reveals a random card from their hand. If it's a land, that player pays 1 life or discards.
        If it isn't a land, the player pays life = its MV or discards it. Activate only during your turn."""
        self.gs.hands[1].clear()
        land = self.g.hand('plains', owner=1)
        non_land = self.g.hand('air-elemental', owner=1)  # mv=5
        card = self.g.card('wand-of-ith')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUUUUUUUUU')
        self.g.activate_ability(aa, 1)

        discard_option = self.gs.pending_choice.options[1]
        first_card_is_land = discard_option.description == 'Discard PLAINS'
        self.gs.choice_mgr.choose(discard_option)
        self.assertIn(land, self.g.gy[1]) if first_card_is_land else self.assertIn(non_land, self.g.gy[1])

        card.untap()
        self.g.activate_ability(aa, 0)
        pay_option = self.gs.pending_choice.options[0]
        self.gs.choice_mgr.choose(pay_option)
        is_land = not first_card_is_land
        life_loss_should_be = 1 if is_land else 5
        self.assertEqual(20 - life_loss_should_be, self.gs.life[1])

    def test_war_barge(self):
        """{3}: Target creature gains islandwalk EOT. When WB LTB EOT, destroy that creature, no regen allowed"""
        card = self.g.battlefield('war-barge')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUUUUU')
        target = self.g.battlefield('scryb-sprites')
        self.g.activate_ability(aa, target)
        self.assertIn(KW.ISLANDWALK, target.keyword_abilities)

        self.g.next_turn()
        self.assertNotIn(KW.ISLANDWALK, target.keyword_abilities)
        self.g.activate_ability(aa, target)
        self.gs.pile_mgr.destroy(target, allow_regeneration=False)
        self.assertIn(card, self.g.gy[0])

    def test_wheel_of_fortune(self):
        """Each player discards their hand, then draws seven cards"""
        original_card_ids = {c.id_ for c in list(self.gs.pile_mgr.hands[0])}
        wheel_of_fortune = self.g.card('wheel-of-fortune')
        wheel_of_fortune.abilities[0].effect.resolve(self.gs, wheel_of_fortune, None)
        current_card_ids = {c.id_ for c in self.gs.pile_mgr.hands[0]}
        self.assertTrue(original_card_ids.isdisjoint(current_card_ids))

    def test_whirlish_dervish(self):
        """At each end step, if WD dealt damage to an opponent this turn, put a +1/+1 counter on it."""
        wd = self.g.battlefield('whirling-dervish')
        self.g.next_turn()
        self.g.combat(wd, None)
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertEqual(2, wd.power)

    def test_worms_of_the_earth(self):
        """Players can't play lands. Lands can't ETB.
        At each upkeep, any player may: do nothing, sac two choice lands, or WOTE deals 5 damage to that player.
        If sac or take the 5 damage, destroy this enchantment."""
        self.g.mana('UU')
        self.g.battlefield('worms-of-the-earth')
        unplayable_land = self.g.hand('swamp')
        self.assertFalse(self.gs.perm_querier.can_cast(unplayable_land, 0))

        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(3, len(self.gs.pending_choice.get_actions()))
        sac_two_lands = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(sac_two_lands)
        self.assertFalse(any(c.is_land for c in self.gs.boards[0]))

        self.g.next_turn(True)
        card = self.g.battlefield('worms-of-the-earth')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, self.gs.action_on_idx)
        self.assertEqual(2, len(self.gs.pending_choice.get_actions()))
        take_5_damage = self.gs.pending_choice.get_actions()[0]
        take_5_damage.play()
        self.assertEqual(15, self.gs.life[1])
        self.assertIn(card, self.g.gy[0])

    def test_xenic_poltergeist(self):
        """Until your next upkeep, target noncreature artifact becomes an artifact creature w PT each = to its MV"""
        target = self.g.battlefield('sol-ring')  # 1
        card = self.g.battlefield('xenic-poltergeist')
        aa = card.activated_abilities[0]

        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertTrue(target.is_creature)
        self.assertEqual(1, target.toughness)

        self.g.next_turn(True)
        self.assertTrue(target.is_creature)
        self.assertEqual(1, target.toughness)

        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertFalse(target.is_creature)
        self.assertEqual(0, target.toughness)

if __name__ == '__main__':
    unittest.main()

