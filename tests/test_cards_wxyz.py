import unittest

from models.constants import KW
from models.events_all import BlockEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame


class TestCardsWXYZ(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_walking_dead(self):
        """{B}: Regenerate this creature."""

    def test_wall_of_bone(self):
        """{B}: Regenerate this creature"""

    def test_wall_of_brambles(self):
        """Defender u003ciu003e(This creature can't attack.)u003c/iu003e {G}: Regenerate this creature."""

    def test_wall_of_dust(self):
        """Whenever this creature blocks, the attacker can't attack during its controller's next turn"""
        card = self.g.battlefield('wall-of-dust')  # 1/4
        attacker = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS)
        self.gs.combat_mgr.add_blocker(attacker, card)
        self.gs.event_mgr.emit(BlockEvent(attacker, card))
        self.gs.combat_mgr.handle_damage_step(False)

        self.g.next_turn()
        self.assertFalse(self.gs.perm_querier.can_attack(attacker))

    def test_wall_of_opposition(self):
        """{1}: This creature gets +1/+0 until end of turn."""

    def test_wall_of_putrid_flesh(self):
        """Protection from white; Prevent all damage that would be dealt to this creature by enchanted creatures."""

    def test_wall_of_tombstones(self):
        """At your upkeep, change WOT's base T to 1 + creatures in your graveyard (This effect lasts indefinitely.)"""

    def test_wall_of_vapor(self):
        """Prevent all damage that would be dealt to this creature by creatures it's blocking"""
        card = self.g.battlefield('wall-of-vapor')  # 0/1
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        com = self.gs.combat_mgr.get_combat(attacker)
        com.add_blocker(card)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertNotIn(card, self.g.gy[0])

    def test_wall_of_water(self):
        """{U}: This creature gets +1/+0 EOT"""

    def test_wall_of_wonder(self):
        """{2UU}: This creature gets +4/-4 EOT and can attack this turn as though it didn't have defender."""

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

    def test_wanderlust(self):
        """At host's upkeep, W deals 1 damage to that player."""

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

    def test_warp_artifact(self):
        """At host's upkeep, WA deals 1 damage to that player."""

    def test_water_wurm(self):
        """This creature gets +0/+1 as long as an opponent controls an Island."""

    def test_weakness(self):
        """Enchant creature Enchanted creature gets -2/-1."""

    def test_weakstone(self):
        """Attacking creatures get -1/-0."""

    def test_web(self):
        """Host gets +0/+2 and has reach"""

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

    def test_white_mana_battery(self):
        """{2T}: Put a charge counter on WMB.
        {T}, Remove any number of charge counters from WMB: Add {W} + {W} * each charge counter removed this way."""

    def test_white_ward(self):
        """Enchant creature Enchanted creature has protection from white. This effect doesn't remove this Aura."""

    def test_wild_growth(self):
        """Enchant land Whenever enchanted land is tapped for mana, its controller adds an additional {G}."""

    def test_will_o_the_wisp(self):
        """{B}: Regenerate WOTW"""

    def test_willow_satyr(self):
        """You may choose not to untap WS during your untap step.
        {T}: Gain control of target legendary creature for as long as you control WS & WS remains tapped."""

    def test_winds_of_change(self):
        """Each player shuffles the cards from their hand into their library, then draws that many cards."""

    def test_winter_blast(self):
        """Tap X target creatures. Winter Blast deals 2 damage to each of those creatures with flying."""

    def test_winter_orb(self):
        """As long as this artifact is untapped, players can't untap more than one land during their untap steps"""
        self.g.battlefield('winter-orb')
        plains = self.g.battlefield('plains')
        swamp = self.g.battlefield('swamp')

        plains.tap()
        swamp.tap()
        self.g.next_turn()
        untap_plains = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(untap_plains)
        self.assertFalse(plains.is_tapped)
        self.assertTrue(swamp.is_tapped)
        self.assertIsNone(self.gs.pending_choice)

        plains.tap()
        swamp.tap()
        self.g.next_turn()
        leave_plains_tapped = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(leave_plains_tapped)
        untap_swamp = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(untap_swamp)
        self.assertTrue(plains.is_tapped)
        self.assertFalse(swamp.is_tapped)
        self.assertIsNone(self.gs.pending_choice)

    def test_witch_hunter(self):
        """{T}: WH deals 1 damage to target player. {1WW}, {T}: Return target opp creature to its owner's hand."""

    def test_wood_elemental(self):
        """As WE ETB, sac any number of untapped Forests. WE's power & toughness each = the Forest cnt sac'ed"""

    def test_wooden_sphere(self):
        """Whenever a player casts a green spell, you may pay {1}. If you do, you gain 1 life."""

    def test_word_of_binding(self):
        """Tap X target creatures."""

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

    def test_wormwood_treefolk(self):
        """{GG}: WT gains forestwalk until end of turn and deals 2 damage to you.
        {BB}: WT gains swampwalk until end of turn and deals 2 damage to you."""

    def test_wrath_of_god(self):
        """Destroy all creatures. They can't be regenerated."""

    def test_wyluli_wolf(self):
        """{T}: Target creature gets +1/+1 until end of turn."""

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

    def test_xira_arien(self):
        """Flying {BRG}, {T}: Target player draws a card."""

    def test_yawgmoth_demon(self):
        """At your upkeep, you may sac an artifact, else tap this creature & it deals 2 damage to you."""

    def test_ydwen_efreet(self):
        """Whenever YE blocks, flip a coin.
        If you lose the flip, remove YE from combat & it can't block this turn.
        Creatures it was blocking that had become blocked by only YE this combat become unblocked."""

    def test_zombie_master(self):
        """Other Zombie creatures have swampwalk.  Other Zombies have '{B}: Regenerate this permanent.'"""
        card = self.g.battlefield('zombie-master')
        zombie = self.g.battlefield('scathe-zombies')  # vanilla card w no abilities
        self.assertIn(KW.SWAMPWALK, zombie.keyword_abilities)
        self.assertNotEqual([], zombie.activated_abilities)

        self.gs.pile_mgr.destroy(card)
        self.assertNotIn(KW.SWAMPWALK, zombie.keyword_abilities)
        self.assertEqual([], zombie.activated_abilities)


if __name__ == '__main__':
    unittest.main()
