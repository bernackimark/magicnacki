import unittest

from models.actions.special import Attach
from models.phase_manager import Phase
from models.zone import Zone
from tests.setup_helpers import TestGame

class TestCardsGHI(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_gaeas_touch_forest_to_battlefield(self):
        """{0}: You may put a basic Forest card from your hand onto the battlefield.
        Activate only as a sorcery and only once each turn."""
        card = self.g.battlefield('gaeas-touch')
        aa = card.activated_abilities[1]
        self.g.mana('G')
        self.g.next_turn()
        forest = self.g.hand('forest')
        self.g.activate_ability(aa, forest)
        self.assertTrue(self.gs.mana_pools[0].can_pay('GG'))
        self.g.hand('forest')
        self.assertFalse(aa.can_activate(self.gs))

    def test_gaeas_touch_add_gg(self):
        """Sacrifice this enchantment: Add {GG}."""
        card = self.g.battlefield('gaeas-touch')
        aa = card.activated_abilities[0]
        self.g.activate_ability(aa, 0)
        self.assertTrue(self.gs.mana_pools[0].can_pay('GG'))
        self.assertIn(card, self.gs.pile_mgr.graveyards[0])

    def test_gaseous_form(self):
        """Prevent all combat damage that would be dealt to and dealt by enchanted creature"""
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        card = self.g.battlefield('gaseous-form')
        Attach(0, self.gs, card, host).play()
        blocker = self.g.battlefield('scryb-sprites')
        self.g.next_turn()
        self.g.combat(host, blocker)
        self.assertTrue(host.zone == Zone.BATTLEFIELD)
        self.assertTrue(blocker.zone == Zone.BATTLEFIELD)

    def test_giant_slug(self):
        """{5}: At your next upkeep, GS gains landwalk of any type until the end of that turn."""
        card = self.g.battlefield('giant-slug')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUU')
        self.g.activate_ability(aa, card)
        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))

    def test_haunting_wind(self):
        """Whenever an artifact becomes tapped or a player activates an artifact's ability
        without {T} in its activation cost, HW deals 1 damage to that artifact's controller."""
        self.g.battlefield('haunting-wind')
        artifact_1 = self.g.battlefield('sol-ring', owner=1)
        artifact_1.tap()
        self.assertEqual(19, self.gs.score_mgr.life[1], '1 damage should be dealt for a tap unrelated to AA')

        artifact_2 = self.g.battlefield('aladdins-ring', owner=1)
        aa = artifact_2.activated_abilities[0]  # {8}, {T}
        self.g.mana('UUUUUUUUUUU')
        self.g.activate_ability(aa, 0)
        self.assertEqual(18, self.gs.score_mgr.life[1], '1 damage should be dealt for AA w tap')

        artifact_3 = self.g.battlefield('jade-statue', owner=1)
        aa = artifact_3.activated_abilities[0]  # {2}
        self.g.mana('RRRR')
        self.g.activate_ability(aa, artifact_3)
        self.assertEqual(17, self.gs.score_mgr.life[1], '1 damage should be dealt for AA w/o tap')

        non_artifact = self.g.battlefield('dragon-whelp')
        aa = non_artifact.activated_abilities[0]
        self.g.mana('R')
        self.g.activate_ability(aa, non_artifact)
        self.assertEqual(17, self.gs.score_mgr.life[1], '0 damage should be dealt for a non-artifact')

    def test_ichneumon_druid(self):
        """Whenever an opponent casts an instant spell other than the first instant spell that player casts each turn,
        ID deals 4 damage to that player."""
        self.g.battlefield('ichneumon-druid')
        self.g.mana('RR', owner=1)
        bolt = self.g.hand('lightning-bolt', owner=1)
        bolt_2 = self.g.hand('lightning-bolt', owner=1)
        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.g.cast_and_accept(bolt_2, 0, bolt_2.abilities[0], owner=1)
        self.assertEqual(16, self.gs.score_mgr.life[1])

    def test_instill_energy(self):
        """Enchanted creature can attack as though it had haste.
        {0}: Untap enchanted creature. Activate only during your turn and only once each turn."""
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        card = self.g.battlefield('instill-energy')
        give_haste_eff_spec = card.abilities[0]
        aa = card.activated_abilities[0]
        give_haste_eff_spec.effect.resolve(self.gs, card, host)  # type: ignore
        self.assertTrue(self.gs.perm_querier.can_attack(host))

        card.tap()
        self.g.activate_ability(aa, host)
        self.assertFalse(host.is_tapped)

        card.tap()
        self.assertFalse(aa.can_activate(self.gs), 'Should not be able to activate 2x in a turn')


if __name__ == '__main__':
    unittest.main()
