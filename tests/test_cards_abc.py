import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import SelectXAction2
from models.actions.special import Attach
from models.cost import SacCardCost
from models.counter_tokens import PLUS_ONE_ZERO, PUPA, STORAGE, DOOM
from models.effects.listeners_misc import ArtifactPossessionActivation
from models.effects.resolvers_a_to_e import BloodLust
from models.events_all import AbilityActivatedEvent, CombatEndEvent, UpkeepEvent, DiscardStepEvent, StateBasedEvent, \
    DrawStepEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCardsAtoC(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_animate_artifact(self):
        card = self.g.hand('animate-artifact')
        host = self.g.battlefield('sol-ring')
        self.g.mana('UUUU')
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.assertEqual(1, host.power)

    def test_animate_dead(self):
        card = self.g.hand('animate-dead')
        target = self.g.battlefield('grizzly-bears')  # 2/2
        bolt = self.g.hand('lightning-bolt')
        self.g.mana('BBB')
        self.g.cast_and_accept(bolt, target, bolt.abilities[0])
        self.assertIn(target, self.g.gy[0])

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.targets.append(target)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(target, self.gs.boards[0])
        self.assertEqual(1, target.power)  # -1/0

    def test_animate_wall(self):
        card = self.g.hand('animate-wall')
        host = self.g.battlefield('wall-of-brambles')

        self.g.next_turn()
        self.assertFalse(self.gs.perm_querier.can_attack(host))
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.assertTrue(self.gs.perm_querier.can_attack(host))

    def test_anti_aura_magic(self):
        card = self.g.hand('anti-magic-aura')
        host = self.g.battlefield('grizzly-bears')
        legal_target = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.cast_and_accept(card, host, card.abilities[2])
        bolt = self.g.hand('lightning-bolt')
        self.assertTrue(self.gs.perm_querier.can_target(legal_target, bolt))
        self.assertFalse(self.gs.perm_querier.can_target(host, bolt))

    def test_armageddon_clock(self):
        """At your upkeep, put a doom counter on AC.
        At your draw step, AC deals damage = its doom counters to each player.
        {4}: Remove a doom counter from AC. Any player may activate this ability but only during any upkeep step."""
        card = self.g.battlefield('armageddon-clock')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertEqual(1, card.counters.get_count(DOOM))

        self.g.next_turn()
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertEqual([19, 19], self.gs.life)
        self.gs.event_mgr.emit(UpkeepEvent(0))

        self.g.next_turn()
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertEqual([17, 17], self.gs.life)
        self.g.mana('RRRR')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(0, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))

        self.g.next_turn(True)
        self.g.mana('WWWW', owner=1)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, self.gs.action_on_idx)
        self.assertTrue(any(a.source is card for a in self.gs.add_activated_abilities_from_board()))

    def test_artifact_possession(self):
        """Whenever enchanted artifact becomes tapped or a player activates an ability of enchanted artifact without {T}
        in its activation cost, this Aura deals 2 damage to that artifact's controller."""
        artifact = self.g.battlefield('barls-cage')  # Activated('3', ...)
        aura = self.g.card('artifact-possession')
        aura.host = artifact
        listener = ArtifactPossessionActivation()
        self.gs.event_mgr.register(listener, aura)
        aa = artifact.activated_abilities[0]
        self.gs.event_mgr.emit(AbilityActivatedEvent(0, aa))
        self.assertEqual(self.gs.life[0], 18)

    def test_berserk(self):
        """Cast this spell only before the combat damage step. Target creature gains trample and gets +X/+0 EOT,
        where X is its power. At end step, destroy that creature if it attacked this turn."""
        self.gs.hands[0].clear()
        card = self.g.hand('berserk')
        target = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.mana('GGG')
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertFalse(any(a for a in self.gs.available_actions_from_hand()
                         if isinstance(a, AbilityPipeline) and a.source is card))

        self.g.next_turn()
        card.abilities[0].effect.resolve(self.gs, card, target)
        self.g.combat(target, None)
        self.assertEqual(16, self.gs.life[1])
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.assertIn(target, self.g.gy[0])

    def test_blazing_effigy(self):
        """When BE dies, it deals X damage to target creature.
        X = 3 + the amount of damage dealt to BE this turn by other sources named 'Blazing Effigy'."""
        card = self.g.battlefield('blazing-effigy')
        be2 = self.g.battlefield('blazing-effigy')
        target = self.g.battlefield('craw-wurm')  # 6/4
        self.gs.apply_damage(be2, 1, card)
        self.gs.pile_mgr.destroy(card)
        deal_4_damage_to_craw_wurm = self.gs.pending_choice.get_actions()[2]
        deal_4_damage_to_craw_wurm.play()
        self.assertIn(target, self.g.gy[0])

    def test_blood_lust(self):
        """If target creature has toughness 5 or greater, it gets +4/-4 until end of turn.
        Otherwise, it gets +4/-X until end of turn, where X is its toughness minus 1."""
        large_creature = self.g.battlefield('bartel-runeaxe')  # 6/5
        small_creature = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        blood_lust = self.g.card('blood-lust', 1)
        BloodLust().resolve(self.gs, blood_lust, large_creature)
        BloodLust().resolve(self.gs, blood_lust, small_creature)
        self.assertEqual(large_creature.power, 10)
        self.assertEqual(large_creature.toughness, 1)
        self.assertEqual(small_creature.power, 5)
        self.assertEqual(small_creature.toughness, 1)

    def test_bone_flute(self):
        """2T: All creatures get -1/-0 until end of turn"""
        # TODO: Bone Flute has a Listener, but it shouldn't be active until its ability is triggered
        creature = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        card = self.g.battlefield('bone-flute')
        aa = card.activated_abilities[0]
        self.g.mana('RRRR')
        self.g.activate_ability(aa)
        self.assertEqual(0, creature.power)

        self.g.next_turn()
        self.assertEqual(1, creature.power)

    def test_brine_hag(self):
        """When BH dies, change base PT of all creatures that dealt damage to it this turn to 0/2.
        (This effect lasts indefinitely.)"""
        card = self.g.battlefield('brine-hag')  # 2/2
        creature = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(creature)
        self.gs.combat_mgr.add_blocker(creature, card)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(0, creature.power)

        self.g.next_turn()
        self.assertEqual(0, creature.power)

    def test_candelabra_of_tawnos(self):
        """{X}, {T}: Untap X target lands"""
        card = self.g.battlefield('candelabra-of-tawnos')
        aa = card.activated_abilities[0]
        swamp = self.g.battlefield('swamp')
        forest = self.g.battlefield('forest')
        self.assertFalse(aa.eff_spec.target_spec.get_targets(self.gs, card))
        swamp.tap()
        forest.tap()
        self.assertEqual(2, len(aa.eff_spec.target_spec.get_targets(self.gs, card)))

        self.g.battlefield('mountain')
        plains = self.g.battlefield('plains')
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.x_value = 2
        pipeline.targets.append(swamp)
        pipeline.targets.append(forest)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertFalse(swamp.is_tapped)
        self.assertTrue(plains.is_tapped)

        self.g.next_turn()
        self.assertEqual(0, len(aa.eff_spec.target_spec.get_targets(self.gs, card)))

    def test_caverns_of_despair(self):
        """No more than two creatures can attack each combat. No more than two creatures can block each combat."""
        self.g.battlefield('caverns-of-despair')
        a1 = self.g.battlefield('scryb-sprites')
        a2 = self.g.battlefield('savannah-lions')
        a3 = self.g.battlefield('tundra-wolves')

        self.g.next_turn()
        self.gs.combat_mgr.create_combat(a1)
        self.assertTrue(self.gs.perm_querier.can_attack(a2))
        self.gs.combat_mgr.create_combat(a2)
        self.assertFalse(self.gs.perm_querier.can_attack(a3))

    def test_city_in_a_bottle(self):
        """Whenever a nontoken permanent with a name originally printed in Arabian Nights is on battlefield, sac it"""
        an_card = self.g.battlefield('serendib-efreet')
        card = self.g.hand('city-in-a-bottle')
        self.g.cast_and_accept(card, None, card.abilities[2])
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertNotIn(an_card, self.gs.boards[0])

    def test_city_of_shadows(self):
        """{T}, Exile a creature you control: Put a storage counter COS.
        {T}: Add {C} * storage counters on SOC."""
        card = self.g.battlefield('city-of-shadows')
        aa2 = card.activated_abilities[1]
        self.assertFalse(aa2.eff_spec.effect.can_activate(self.gs, card))  # type: ignore

        aa1 = card.activated_abilities[0]
        creature = self.g.battlefield('savannah-lions')
        pipeline = AbilityPipeline(0, self.gs, card, aa1.eff_spec,
                                   selected_extra_costs=[SacCardCost(selected_card=creature)])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(1, card.counters.get_count(STORAGE))
        self.assertIn(creature, self.g.gy[0])

        self.g.next_turn()
        self.g.activate_ability(aa2)
        self.assertEqual(1, self.gs.mana_pools[0].available_mana.get('C'))

    def test_clergy_of_the_nimbus(self):
        """If COTN would be destroyed, regenerate it.
        {1}: COTN can't be regenerated this turn. Only your opponents may activate this ability."""
        card = self.g.battlefield('clergy-of-the-holy-nimbus')
        self.gs.pile_mgr.destroy(card)
        self.assertIn(card, self.gs.boards[0])

        self.gs.pile_mgr.destroy(card, allow_regeneration=False)
        self.assertIn(card, self.g.gy[0])

        card = self.g.battlefield('clergy-of-the-holy-nimbus')
        aa = card.activated_abilities[0]
        self.g.next_turn(True)
        self.g.mana('G', owner=1)
        self.g.activate_ability(aa, card, owner=1)
        self.gs.pile_mgr.destroy(card)
        self.assertIn(card, self.g.gy[0])

    def test_clockwork_avian(self):
        """CA enters with four +1/+0 counters. At combat end, if CA attacked or blocked, remove a +1/+0 counter from it.
        {X}, {T}: Put up to X +1/+0 counters on CA. Can't exceed 4 such counters. Activate only during your upkeep."""
        card = self.g.battlefield('clockwork-avian')
        self.g.resolve_spell(card, card)
        aa = card.activated_abilities[0]
        self.assertEqual(4, card.counters.get_count(PLUS_ONE_ZERO))
        self.g.mana('UUUUUUUU')

        for i in range(1, 3):
            self.g.next_turn()
            self.g.combat(card, None)
            self.gs.event_mgr.emit(CombatEndEvent(0))
            self.assertEqual(4 - i, card.counters.get_count(PLUS_ONE_ZERO))

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.advance()
        x_options_cnt = len([a for a in self.gs.pending_choice.get_actions() if isinstance(a, SelectXAction2)])
        self.assertEqual(2, x_options_cnt, "Should only be able to activate for X=1 or X=2, due to counter cap of 4")

    def test_clockwork_beast(self):
        """CA enters with 7 +1/+0 counters. At combat end, if CA attacked or blocked, remove a +1/+0 counter from it.
        {X}, {T}: Put up to X +1/+0 counters on CB. Can't exceed 7 such counters. Activate only during your upkeep."""
        card = self.g.battlefield('clockwork-beast')
        self.g.resolve_spell(card, card)
        aa = card.activated_abilities[0]
        self.assertEqual(7, card.counters.get_count(PLUS_ONE_ZERO))
        self.g.mana('UUUUUUUU')

        for i in range(1, 4):
            self.g.next_turn()
            self.g.combat(card, None)
            self.gs.event_mgr.emit(CombatEndEvent(0))
            self.assertEqual(7 - i, card.counters.get_count(PLUS_ONE_ZERO))

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.advance()
        x_options_cnt = len([a for a in self.gs.pending_choice.get_actions() if isinstance(a, SelectXAction2)])
        self.assertEqual(3, x_options_cnt, "Should only be able to activate for X=1, 2, or 3, due to counter cap of 7")

    def test_cocoon(self):
        """Enchant creature you control. When this Aura enters, tap host & put 3 pupa counters on C.
        Host doesn't untap during your untap step if C has a pupa counter on it.
        At your upkeep, remove a pupa counter from C.
        If you can't, sac C, put a +1/+1 counter on host & host gains flying."""
        card = self.g.hand('cocoon')
        host = self.g.battlefield('savannah-lions')  # 2/1
        self.g.mana('GGG')
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.assertTrue(host.is_tapped)
        self.assertEqual(3, card.counters.get_count(PUPA))

        for i in range(1, 4):
            self.g.next_turn()
            self.gs.event_mgr.emit(UpkeepEvent(0))
            self.assertEqual(3 - i, card.counters.get_count(PUPA))
            self.assertTrue(host.is_tapped)

        self.g.next_turn()
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertIn(card, self.g.gy[0])
        self.assertEqual(3, host.power)
        self.assertIn('Flying', host.keyword_abilities)

    def test_concordant_crossroads(self):
        """All creatures have haste"""
        creature = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.assertFalse(self.gs.perm_querier.can_attack(creature))
        self.g.battlefield('concordant-crossroads')
        self.assertTrue(self.gs.perm_querier.can_attack(creature))

    def test_consecrate_land(self):
        """Host has indestructible and can't be enchanted by other Auras"""
        card = self.g.battlefield('consecrate-land')
        host = self.g.battlefield('island')
        unprotected_land = self.g.battlefield('swamp')
        Attach(0, self.gs, card, host).play()

        phantasmal_terrain = self.g.card('phantasmal-terrain')
        targets = phantasmal_terrain.abilities[0].target_spec.get_targets(self.gs, phantasmal_terrain)
        self.assertIn(unprotected_land, targets)
        self.assertNotIn(host, targets)

        # TODO: once Indestructible is coded, uncomment this test
        # stone_rain = self.g.card('stone-rain')
        # stone_rain.abilities[0].effect.resolve(self.gs, stone_rain, host)  # type: ignore
        # self.assertNotIn(host, self.g.gy[0])

    # def test_creature_bond(self):
    #     """When host dies, this Aura deals damage equal to that creature's toughness to the creature's controller."""
    #     # TODO: By the time CreatureBond.on_event() is called, the source.host is None;
    #     #  I'm guessing the aura is detached already
    #     host = get_card(self.gs, 'merfolk-of-the-pearl-trident', 0)  # 1/1
    #     creature_bond = get_card(self.gs, 'creature-bond', 1)
    #     host.auras.append(creature_bond)
    #     self.gs.event_mgr.register(creature_bond.abilities[0].effect, creature_bond)
    #     self.gs.pile_mgr.destroy(host)
    #     self.assertEqual(self.gs.life[0], 19)

    def test_cuombajj_witches(self):
        """{T}: CW deals 1 damage to any target and 1 damage to any target of an opponent's choice."""
        card = self.g.battlefield('cuombajj-witches')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('savannah-lions', owner=1)
        self.g.activate_ability(aa, target)
        self.assertIn(target, self.g.gy[1])
        deal_1_damage_to_play_0 = self.gs.pending_choice.get_actions()[1]
        deal_1_damage_to_play_0.play()
        self.assertEqual(19, self.gs.life[0])

    def test_cursed_rack(self):
        """Opponent's maximum hand size is four [at their discard phase]"""
        self.g.battlefield('cursed-rack')
        opp_hand = self.gs.hands[1]
        opp_hand.pop()
        self.assertTrue(len(opp_hand) == 6)
        self.g.next_turn(True)
        self.gs.event_mgr.emit(DiscardStepEvent(1))
        self.assertEqual(15, len(self.gs.pending_choice.get_actions()))  # 6 card hand x 2 selections = 15 combos


if __name__ == '__main__':
    unittest.main()
