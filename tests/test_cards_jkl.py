import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.counter_tokens import MINUS_ZERO_ONE
from models.systems.phase import Phase
from models.zone import Zone
from tests.setup_helpers import TestGame

class TestCardsJKL(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_jade_monolith(self):
        """{1}: The next time a source of your choice would deal damage to target creature this turn,
        that source deals that damage to you instead"""
        # WARNING: I'm not actually checking for the source, it's any next damage to the protected target creature
        card = self.g.battlefield('jade-monolith')
        target = self.g.battlefield('grizzly-bears')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('B')
        self.g.mana('R', owner=1)
        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[target])
        bolt_pipeline.advance()
        self.g.activate_ability(card.activated_abilities[0], target)
        bolt_pipeline.resolve_ability()
        self.assertIn(target, self.gs.boards[0])
        self.assertEqual(17, self.gs.life[0])

    def test_johan(self):
        """At your combat begin step, you may have J gain Defender & your creatures gain Vigilance EOT.
        If J becomes tapped, your creatures lose their Vigilance."""
        card = self.g.battlefield('johan')
        c1 = self.g.battlefield('grizzly-bears')
        c2 = self.g.battlefield('serendib-efreet')

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.DECLARE_ATTACKERS)
        johan_action = self.gs.pending_choice.get_actions()[0]
        johan_action.play()
        self.assertIn('Defender', card.keyword_abilities)
        self.assertIn('Vigilance', c1.keyword_abilities)

        card.tap()
        self.assertIn('Defender', card.keyword_abilities)
        self.assertNotIn('Vigilance', c1.keyword_abilities)
        self.assertNotIn('Vigilance', c2.keyword_abilities)


    def test_jovial_evil(self):
        """JE deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
        self.g.battlefield('savannah-lions', owner=1)
        card = self.g.hand('jovial-evil')
        card.abilities[0].effect.resolve(self.gs, card, 1)  # type: ignore
        self.assertEqual(18, self.gs.life[1])

    # def test_kudzu(self):
    #     """When host becomes tapped, destroy it. Host may attach this Aura to a land of their choice."""
    #     # TODO: aura is already sent to graveyard upon its host being destroyed, just like creature-bond
    #     card = self.g.hand('kudzu')
    #     target = self.g.battlefield('island', owner=1)
    #     other_target_1 = self.g.battlefield('swamp', owner=1)
    #     other_target_2 = self.g.battlefield('plains', owner=1)
    #     self.g.cast_and_accept(card, target, card.abilities[1])
    #     target.tap()
    #     self.assertIn(target, self.g.gy[1])
    #     print(self.gs.pending_choice)

    def test_land_equilibrium(self):
        """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
        that player instead puts that land onto the battlefield then sacrifices a land of their choice;
        the effect listens to ZoneChangeEvent where zone.to_zone == Zone.BATTLEFIELD"""
        self.g.battlefield('land-equilibrium')
        self.g.mana('RR')
        self.g.mana('BG', owner=1)
        opp_land = self.g.hand('island', owner=1)
        self.gs.pile_mgr.move_card(opp_land, Zone.BATTLEFIELD, cause='cast', emit_zone_event=True)
        self.assertEqual(3, len(self.gs.pending_choice.get_actions()), 'Should have options to sac one of 3 lands')

        self.gs.pending_choice = None
        self.g.mana('RRRRR')
        opp_land = self.g.hand('swamp', owner=1)
        self.gs.pile_mgr.move_card(opp_land, Zone.BATTLEFIELD, cause='cast', emit_zone_event=True)
        self.assertEqual(None, self.gs.pending_choice, 'Should not trigger if you own more lands')

    def test_lesser_werewolf(self):
        """{B}: If LW's power is >= 1, it gets -1/-0 EOT &
        put a -0/-1 counter on target creature blocking or blocked by LW.
        Activate only during the declare blockers step."""
        card = self.g.battlefield('lesser-werewolf')  # 2/4
        aa = card.activated_abilities[0]
        blocker = self.g.battlefield('giant-spider', owner=1)  # 2/4
        self.g.mana('B')

        self.g.next_turn()
        ability = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        self.assertFalse(ability.can_begin())
        self.gs.combat_mgr.create_combat(card)
        com = self.gs.combat_mgr.get_combat(card)
        com.blockers.append(blocker)
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS)
        self.g.activate_ability(aa, blocker)
        self.assertEqual(1, card.power)
        self.assertEqual(1, blocker.counters.get_count(MINUS_ZERO_ONE))

        self.g.next_turn()
        self.assertEqual(2, card.power)

    def test_leviathan(self):
        """This creature enters tapped and doesn't untap during your untap step.
        At your upkeep, you may sac two Islands to untap this creature.
        This creature can't attack unless you sacrifice two Islands. (This cost is paid as attackers are declared.)"""
        card = self.g.hand('leviathan')
        self.g.mana('UUUUUUUUUUUUUUUUUUU')

        pipeline = AbilityPipeline(0, self.gs, card, card.spells[0], targets=[card])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertTrue(card.is_tapped)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        untap = self.gs.pending_choice.get_actions()[0]
        untap.play()
        self.assertFalse(card.is_tapped)
        self.assertFalse(self.gs.perm_querier.can_attack(card))

        self.gs.phase_mgr.set_phase(Phase.MAIN)
        pay_to_attack = self.gs.pending_choice.get_actions()[0]
        pay_to_attack.play()
        self.assertTrue(self.gs.perm_querier.can_attack(card))
        card.tap()

        self.g.next_turn()
        self.assertTrue(card.is_tapped)

    def test_library_of_alexandria(self):
        """{T}: Add {C}.
        {T}: Draw a card. Activate only if you have exactly seven cards in hand."""
        card = self.g.battlefield('library-of-alexandria')
        aa_add_mana = card.activated_abilities[0]
        aa_draw_card = card.activated_abilities[1]

        self.g.activate_ability(aa_add_mana, 0)
        self.assertEqual(1, self.gs.mana_pools[0].available_mana.get('C'))

        self.g.next_turn()
        self.assertEqual(7, len(self.gs.pile_mgr.hands[0]))
        ability = AbilityPipeline(0, self.gs, card, aa_draw_card.eff_spec)
        self.assertTrue(ability.can_begin())
        self.g.activate_ability(aa_draw_card, 0)

        self.g.next_turn()
        self.assertTrue(8, len(self.gs.pile_mgr.hands[0]))
        ability = AbilityPipeline(0, self.gs, card, aa_draw_card.eff_spec)
        self.assertFalse(ability.can_begin())


if __name__ == '__main__':
    unittest.main()
