import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastWithNoSpellEffect
from models.events_all import EndStepEvent, CombatEndEvent, DrawStepEvent
from models.systems.phase import Phase
from models.constants import Zone
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
        ability = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        self.assertFalse(ability.can_begin())

    def test_gaeas_touch_add_gg(self):
        """Sacrifice this enchantment: Add {GG}."""
        card = self.g.battlefield('gaeas-touch')
        aa = card.activated_abilities[0]
        self.g.activate_ability(aa, 0)
        self.assertTrue(self.gs.mana_pools[0].can_pay('GG'))
        self.assertIn(card, self.g.gy[0])

    def test_gaseous_form(self):
        """Prevent all combat damage that would be dealt to and dealt by enchanted creature"""
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        card = self.g.battlefield('gaseous-form')
        self.g.attach(card, host)
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
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))

    def test_glyph_of_destruction(self):
        """Target blocking Wall you control gets +10/+0 until end of combat.
        Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
        card = self.g.hand('glyph-of-destruction')
        wall = self.g.battlefield('wall-of-bone')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        com = self.gs.combat_mgr.get_combat(attacker)
        com.add_blocker(wall)
        self.g.cast_and_accept(card, wall, card.abilities[0])
        self.assertTrue(wall.power > 9)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(0, wall.damage_dealt_this_turn)
        self.gs.event_mgr.emit(EndStepEvent(0))
        self.assertIn(wall, self.g.gy[0])

    def test_glyph_of_doom(self):
        """At combat end, destroy all creatures that were blocked by that target wall this turn."""
        card = self.g.hand('glyph-of-doom')
        wall = self.g.battlefield('wall-of-brambles')  # 2/3
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.g.cast_and_accept(card, wall, card.abilities[0])
        self.g.combat(attacker, wall)
        self.gs.event_mgr.emit(CombatEndEvent(0))
        self.assertIn(attacker, self.g.gy[1])

    def test_glyph_of_life(self):
        """Whenever target wall is dealt damage by an attacking creature this turn, you gain that much life."""
        card = self.g.hand('glyph-of-life')
        wall = self.g.battlefield('wall-of-brambles')  # 2/3
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.g.cast_and_accept(card, wall, card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.assertTrue(attacker.zone == Zone.BATTLEFIELD)
        self.assertTrue(wall.zone == Zone.BATTLEFIELD)
        self.g.combat(attacker, wall)
        self.assertEqual(26, self.gs.life[0])

    def test_goblin_shrine(self):
        """As long as host is a basic Mountain, all Goblins get +1/+0. When GS LTB, it deals 1 damage to each Goblin"""
        card = self.g.hand('goblin-shrine')
        host = self.g.battlefield('mountain')
        self.g.cast_and_accept(card, host, card.abilities[0])
        goblin = self.g.battlefield('monss-goblin-raiders')  # 1/1
        self.assertEqual(2, goblin.power)
        self.gs.pile_mgr.destroy(card)
        self.assertIn(goblin, self.g.gy[0])  # this test now fails

    def test_guardian_beast(self):
        """As long as GB is untapped, noncreature artifacts you control can't be enchanted, they have indestructible, &
        other players can't gain control of them. This effect doesn't remove Auras already attached."""
        # TODO: other players can't gain control of them
        card = self.g.battlefield('guardian-beast')
        protected = self.g.battlefield('sol-ring')
        artifact_destroyer = self.g.hand('disenchant')
        artifact_aura = self.g.hand('artifact-possession')
        self.g.mana('BBBWWW')

        self.assertFalse(self.gs.perm_querier.can_target(protected, artifact_aura))
        card.tap()
        self.assertTrue(self.gs.perm_querier.can_target(protected, artifact_aura))

        card.untap()
        destroy_pipeline = AbilityPipeline(0, self.gs, artifact_destroyer, artifact_destroyer.abilities[0],
                                           targets=[protected])
        destroy_pipeline.advance()
        destroy_pipeline.resolve_ability()
        self.assertIn(protected, self.gs.boards[0])

    def test_halfdane(self):
        """H's base PT = (3, 3)
        At your upkeep, change H's base PT = PT of target creature other than H until end of your NEXT upkeep
        If no legal targets, H's base PT = (3, 3)"""
        card = self.g.battlefield('halfdane')
        self.assertEqual((3, 3), card.base_pt)
        creature1 = self.g.battlefield('sengir-vampire')  # 4/4
        creature2 = self.g.battlefield('grizzly-bears')  # 2/2
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        set_pt_eq_to_sengir = self.gs.pending_choice.get_actions()[0]
        print(set_pt_eq_to_sengir)
        set_pt_eq_to_sengir.play()
        self.assertEqual(4, card.power)

        self.g.next_turn()
        self.gs.pile_mgr.destroy(creature1)
        self.gs.pile_mgr.destroy(creature2)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(3, card.power)

    def test_haunting_wind(self):
        """Whenever an artifact becomes tapped or a player activates an artifact's ability
        without {T} in its activation cost, HW deals 1 damage to that artifact's controller."""
        self.g.battlefield('haunting-wind')
        artifact_1 = self.g.battlefield('sol-ring', owner=1)
        artifact_1.tap()
        self.assertEqual(19, self.gs.life[1], '1 damage should be dealt for a tap unrelated to AA')

        artifact_2 = self.g.battlefield('aladdins-ring', owner=1)
        aa = artifact_2.activated_abilities[0]  # {8}, {T}
        self.g.mana('UUUUUUUUUUU')
        self.g.activate_ability(aa, 0)
        self.assertEqual(18, self.gs.life[1], '1 damage should be dealt for AA w tap')

        artifact_3 = self.g.battlefield('jade-statue', owner=1)
        aa = artifact_3.activated_abilities[0]  # {2}
        self.g.mana('RRRR')
        self.g.activate_ability(aa, artifact_3)
        self.assertEqual(17, self.gs.life[1], '1 damage should be dealt for AA w/o tap')

        non_artifact = self.g.battlefield('dragon-whelp')
        aa = non_artifact.activated_abilities[0]
        self.g.mana('R')
        self.g.activate_ability(aa, non_artifact)
        self.assertEqual(17, self.gs.life[1], '0 damage should be dealt for a non-artifact')

    def test_ichneumon_druid(self):
        """Whenever an opponent casts an instant spell other than the first instant spell that player casts each turn,
        ID deals 4 damage to that player."""
        self.g.battlefield('ichneumon-druid')
        self.g.mana('RR', owner=1)
        bolt = self.g.hand('lightning-bolt', owner=1)
        bolt_2 = self.g.hand('lightning-bolt', owner=1)
        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.g.cast_and_accept(bolt_2, 0, bolt_2.abilities[0], owner=1)
        self.assertEqual(16, self.gs.life[1])

    def test_in_the_eye_of_chaos(self):
        """Whenever a player casts an instant spell, counter it unless that player pays {X}, where X = its mana value"""
        self.g.battlefield('in-the-eye-of-chaos')
        self.g.mana('WWWWWWWWWW')
        instant = self.g.hand('swords-to-plowshares')
        creature = self.g.battlefield('grizzly-bears')

        instant_pipeline = AbilityPipeline(0, self.gs, instant, instant.abilities[0], targets=[creature])
        instant_pipeline.advance()
        pay_mana_to_not_have_countered = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_mana_to_not_have_countered)
        instant_pipeline.resolve_ability()
        self.assertIn(creature, self.gs.exiles[0])

        sorcery = self.g.hand('wrath-of-god')
        creature = self.g.battlefield('monss-goblin-raiders')
        sorcery_pipeline = AbilityPipeline(0, self.gs, sorcery, sorcery.abilities[0], targets=[creature])
        sorcery_pipeline.advance()
        self.assertFalse(self.gs.pending_choice)

    def test_instill_energy(self):
        """Enchanted creature can attack as though it had haste.
        {0}: Untap enchanted creature. Activate only during your turn and only once each turn."""
        host = self.g.battlefield('merfolk-of-the-pearl-trident')
        card = self.g.hand('instill-energy')
        self.g.cast_and_accept(card, host, card.abilities[0])
        give_haste_eff_spec = card.abilities[0]
        aa = card.activated_abilities[0]
        give_haste_eff_spec.effect.resolve(self.gs, card, host)
        self.assertTrue(self.gs.perm_querier.can_attack(host))

        card.tap()
        self.g.activate_ability(aa, host)
        self.assertFalse(host.is_tapped)

        card.tap()
        ability = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        self.assertFalse(ability.can_begin(), 'Should not be able to activate 2x in a turn')

    def test_invoke_prejudice(self):
        """Whenever an opponent casts a creature spell that DOESN'T SHARE A COLOR with a creature you control,
        counter that spell unless that player pays {X}, X = its mana value"""
        self.g.battlefield('invoke-prejudice')
        self.g.battlefield('grizzly-bears')
        self.g.battlefield('will-o-the-wisp')
        unaffected = self.g.hand('chromium', owner=1)  # WUB
        affected = self.g.hand('savannah-lions', owner=1)
        self.g.mana('WWWWUUUUBBBB', owner=1)

        unaffected_pipeline = AbilityPipeline(1, self.gs, unaffected, unaffected.abilities[0])
        unaffected_pipeline.advance()
        self.assertFalse(self.gs.pending_choice)
        unaffected_pipeline.resolve_ability()

        CastWithNoSpellEffect(1, self.gs, affected).play()
        self.assertTrue(self.gs.pending_choice.get_actions())

    def test_island_sanctuary(self):
        """At your draw step, you may skip your draw and until your next turn,
        you can only be attacked by creatures with flying and/or islandwalk"""
        self.g.battlefield('island-sanctuary')
        illegal_attacker = self.g.battlefield('grizzly-bears', owner=1)
        legal_attacker = self.g.battlefield('scryb-sprites', owner=1)
        hand_len = len(self.gs.hands[0])

        self.g.next_turn()
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertEqual(hand_len, len(self.gs.hands[0]))
        skip_draw_and_gain_protection_action = self.gs.pending_choice.get_actions()[0]
        skip_draw_and_gain_protection_action.play()

        self.g.next_turn(True)
        self.assertTrue(self.gs.perm_querier.can_attack(legal_attacker))
        self.assertFalse(self.gs.perm_querier.can_attack(illegal_attacker))

        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        do_nothing_action = self.gs.pending_choice.get_actions()[1]
        do_nothing_action.play()
        self.assertEqual(8, len(self.gs.hands[0]))
        self.gs.hands[0].clear()

        self.g.next_turn(True)
        self.assertTrue(self.gs.perm_querier.can_attack(legal_attacker))
        self.assertTrue(self.gs.perm_querier.can_attack(illegal_attacker))



if __name__ == '__main__':
    unittest.main()
