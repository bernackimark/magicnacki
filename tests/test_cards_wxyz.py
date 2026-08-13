import unittest

from models.constants import KW
from models.systems.phase import Phase
from models.zone import Zone
from tests.setup_helpers import TestGame


class TestCardsWXYZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_wand_of_ith(self):
        """3T: Target player reveals a random card from their hand. If it's a land, that player pays 1 life or discards.
        If it isn't a land, the player pays life = its MV or discards it. Activate only during your turn."""
        card = self.g.card('wand-of-ith')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUUU')
        self.g.activate_ability(aa, 0)
        pay_option = self.gs.pending_choice.options[0]
        discard_option = self.gs.pending_choice.options[1]
        discard_card = discard_option.cards
        if discard_card.is_land:
            pay_option.play()
            self.assertEqual(19, self.gs.life[0])
        else:
            mv = discard_card.props.mana_value
            pay_option.play()
            self.assertEqual(20 - mv, self.gs.life[0])

        self.g.next_turn()
        self.g.activate_ability(aa, 0)
        discard_option = self.gs.pending_choice.options[1]
        discard_card = discard_option.cards
        discard_option.play()
        self.assertEqual(discard_card.zone, Zone.GRAVEYARD)

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
        sac_two_lands.play()
        self.assertFalse(any(c.is_land for c in self.gs.boards[0]))

        self.g.next_turn(True)
        card = self.g.battlefield('worms-of-the-earth')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
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

