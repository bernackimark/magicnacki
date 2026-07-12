import unittest

from models.phase_manager import Phase
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
        if discard_option.cards.is_land:
            pay_option.play()
            self.assertEqual(19, self.gs.score_mgr.life[0])
        else:
            mv = discard_option.cards.props.mana_value
            pay_option.play()
            self.assertEqual(20 - mv, self.gs.score_mgr.life[0])

        self.g.next_turn()
        self.g.activate_ability(aa, 0)
        discard_option = self.gs.pending_choice.options[1]
        discard_option.play()
        discarded_card = discard_option.cards[0]
        self.assertEqual(discarded_card.zone, Zone.GRAVEYARD)

    def test_wheel_of_fortune(self):
        """Each player discards their hand, then draws seven cards"""
        original_card_ids = {c.id_ for c in list(self.gs.pile_mgr.hands[0].cards)}
        wheel_of_fortune = self.g.card('wheel-of-fortune')
        wheel_of_fortune.abilities[0].effect.resolve(self.gs, wheel_of_fortune, None)  # type: ignore
        current_card_ids = {c.id_ for c in self.gs.pile_mgr.hands[0].cards}
        self.assertTrue(original_card_ids.isdisjoint(current_card_ids))

    def test_whirlish_dervish(self):
        """At each end step, if WD dealt damage to an opponent this turn, put a +1/+1 counter on it."""
        wd = self.g.battlefield('whirling-dervish')
        self.g.next_turn()
        self.g.combat(wd, None)
        self.gs.phase_mgr.set_phase(Phase.END_STEP, self.gs)
        self.assertEqual(2, wd.power)


if __name__ == '__main__':
    unittest.main()

