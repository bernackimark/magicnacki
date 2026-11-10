import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import AbilityAction, SelectXAction2
from models.game_card.counter_tokens import HUNGER
from models.events_all import UpkeepEvent
from models.systems.phase import Phase
from models.constants import Zone
from tests.setup_helpers import TestGame


class TestCardsDEF(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_dakkon_blackblade(self):
        """Dakkon Blackblade's power and toughness are each equal to the number of lands you control."""

    def test_damping_field(self):
        """Players can't untap more than one artifact during their untap steps."""
        self.g.battlefield('damping-field')
        a1 = self.g.battlefield('sol-ring')
        a1.tap()

        self.g.next_turn()
        self.assertFalse(a1.is_tapped)  # if only one tapped artifact, the choice is not offered

        a2 = self.g.battlefield('colossus-of-sardia')
        a1.tap()
        a2.tap()

        self.g.next_turn()
        untap_a1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(untap_a1)
        self.assertFalse(a1.is_tapped)
        self.assertTrue(a2.is_tapped)
        self.assertIsNone(self.gs.pending_choice)

        a1.tap()
        a2.tap()
        self.g.next_turn()
        self.assertTrue(a1.is_tapped)
        self.assertTrue(a2.is_tapped)
        leave_all_tapped = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(leave_all_tapped)
        self.assertTrue(a1.is_tapped)
        self.assertTrue(a2.is_tapped)
        self.assertIsNone(self.gs.pending_choice)

    def test_dance_of_many(self):
        """... When DOM ETB, create a token copy of target nontoken creature -- copies its original props w/o mods ...
        When DOM LTB, exile the token. When the token LTB, sac DOM"""
        card = self.g.hand('dance-of-many')
        target = self.g.battlefield('grizzly-bears')  # 2/2
        aura = self.g.hand('holy-strength')  # +1/+2
        self.g.cast_and_accept(aura, target, aura.abilities[0])
        self.assertEqual(3, target.power)

        self.g.cast_and_accept(card, target, card.abilities[1])
        the_copy = next(c for c in self.gs.boards[0] if not c.is_land and c not in (card, target, aura))
        self.assertEqual(Zone.BATTLEFIELD, the_copy.zone)
        self.assertEqual(2, the_copy.power)

        self.g.next_turn()
        self.assertTrue(self.gs.perm_querier.can_attack(the_copy))

        self.gs.pile_mgr.sacrifice(card)
        self.assertNotIn(the_copy, self.gs.boards[0])

    def test_dark_heart_of_the_wood(self):
        """Sacrifice a Forest: You gain 3 life."""

    def test_dark_ritual(self):
        """Add {BBB}."""

    def test_dark_sphere(self):
        """{T}, sac DS: The next time a source of your choice would deal damage to you this turn, prevent it // 2"""

    def test_darkness(self):
        """Prevent all combat damage that would be dealt this turn."""

    def test_davenant_archer(self):
        """{T}: This creature deals 1 damage to target attacking or blocking creature."""

    def test_deadfall(self):
        """Creatures with forestwalk can be blocked as though they didn't have forestwalk."""

    def test_deathgrip(self):
        """{BB}: Counter target green spell."""

    def test_deathlace(self):
        """Target spell or permanent becomes black"""

    def test_death_ward(self):
        """Regenerate target creature."""

    def test_deep_water(self):
        """{U}: Until end of turn, if you tap a land you control for mana, it produces {U} instead of any other type."""

    def test_demonic_hordes(self):
        """... At your upkeep, pay {BBB} or tap this creature and sacrifice a land of an opponent's choice"""
        card = self.g.battlefield('demonic-hordes')

        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertTrue(card.is_tapped)

        card.untap()
        s1 = self.g.battlefield('swamp')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertTrue(card.is_tapped)
        self.assertIn(s1, self.g.gy[0])

        card.untap()
        self.g.battlefield('swamp')
        self.g.battlefield('swamp')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, self.gs.action_on_idx)
        destroy_s1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(destroy_s1)
        self.assertTrue(card.is_tapped)
        self.assertEqual(2, len(self.g.gy[0]))
        self.assertIsNone(self.gs.pending_choice)
        self.assertEqual(0, self.gs.action_on_idx)

        card.untap()
        self.g.mana('BB')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        pay_mana = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_mana)
        self.assertEqual(0, self.gs.mana_pools[0].available_mana.get('B'))
        self.assertIsNone(self.gs.pending_choice)

    def test_demonic_torment(self):
        """Host can't attack. Prevent all combat damage that would be dealt by host."""
        card = self.g.hand('demonic-torment')
        host = self.g.battlefield('grizzly-bears')
        attacker = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        self.g.cast_and_accept(card, host, card.abilities[0])

        self.g.next_turn()
        self.assertFalse(self.gs.perm_querier.can_attack(host))

        self.g.next_turn(True)
        self.g.combat(attacker, host)
        self.assertIn(host, self.gs.pile_mgr.boards[0])

    def test_demonic_tutor(self):
        """Search your library for a card, put that card into your hand, then shuffle."""

    def test_desert(self):
        """{T}: Add {C}. {T}: D deals 1 damage to target attacker. Activate only during the end of combat step."""

    def test_desert_twister(self):
        """Destroy target permanent."""

    def test_detonate(self):
        """Destroy target artifact with MV X (no regen allowed). D deals X damage to that artifact's controller.
        Note: if X does not match the target MV, the effect will fizzle."""
        self.gs.hands[0].clear()
        card = self.g.hand('detonate')  # XR
        self.g.mana('R')
        mox = self.g.battlefield('mox-emerald', owner=1)  # MV=0

        # The target's MV matches X, proceed.  X=0
        pipeline_v_mox = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=0, targets=[mox])
        pipeline_v_mox.advance()
        pipeline_v_mox.resolve_ability()
        self.assertIn(mox, self.g.gy[1])
        self.assertEqual(20, self.gs.life[1])

        # The target's MV does not match X, fizzle
        card = self.g.hand('detonate')  # XR
        self.g.mana('R')
        juggernaut = self.g.battlefield('juggernaut', owner=1)  # MV=4
        pipeline_v_juggernaut = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=0, targets=[juggernaut])
        pipeline_v_juggernaut.advance()
        pipeline_v_juggernaut.resolve_ability()
        self.assertNotIn(juggernaut, self.g.gy[1])
        self.assertEqual(20, self.gs.life[1])

        # The target's MV matches X, proceed.  X>1
        self.gs.hands[0].clear()
        card = self.g.hand('detonate')  # XR
        self.g.mana('RRR')
        mine = self.g.battlefield('howling-mine', owner=1)  # MV=2
        pipeline_v_mine = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=2, targets=[mine])
        pipeline_v_mine.advance()
        pipeline_v_mine.resolve_ability()
        self.assertIn(mine, self.g.gy[1])
        self.assertEqual(18, self.gs.life[1])

    def test_diabolic_machine(self):
        """{3}: Regenerate this creature."""

    def test_diamond_valley(self):
        """{T}, Sacrifice a creature: You gain life equal to the sacrificed creature's toughness."""

    def test_dingus_egg(self):
        """Whenever a land is put into a graveyard from the battlefield, DE deals 2 damage to that land's controller."""

    def test_disharmony(self):
        """Cast this spell only during combat before blockers are declared.
        Untap target attacking creature and remove it from combat. Gain control of that creature EOT."""
        card = self.g.hand('disharmony')
        attacker = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        self.g.cast_and_accept(card, attacker, card.abilities[0])
        self.assertEqual(0, attacker.owner_id)

        self.g.next_turn(True)
        self.assertEqual(1, attacker.owner_id)

    def test_disintegrate(self):
        """D deals X damage to any target.
        If it's a creature, no regen allow EOT, & if it would die EOT, exile instead."""
        card = self.g.hand('disintegrate')
        self.g.mana('RRRRR')
        target = self.g.battlefield('will-o-the-wisp', owner=1)

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[target])
        x_action = SelectXAction2(0, self.gs, pipeline, 4)
        x_action.play()
        pipeline.advance()
        self.assertFalse(self.gs.pending_choice)
        pipeline.resolve_ability()
        self.assertIn(target, self.gs.exiles[1])

    def test_disrupting_scepter(self):
        """{3}, {T}: Target player discards a card. Activate only during your turn."""

    def test_disenchant(self):
        """Destroy target artifact or enchantment."""

    def test_divine_offering(self):
        """Destroy target artifact. You gain life equal to its mana value."""

    def test_divine_transformation(self):
        """Enchant creature Enchanted creature gets +3/+3."""

    def test_drafnas_restoration(self):
        """Put any number of target artifact cards from target player's graveyard atop of their library in ANY ORDER"""
        card = self.g.hand('drafnas-restoration')
        aladdins_lamp = self.g.graveyard('aladdins-lamp')
        self.g.graveyard('basalt-monolith')
        colossus = self.g.graveyard('colossus-of-sardia')
        self.g.graveyard('dwarven-warriors')  # not an artifact
        self.g.cast_and_accept(card, 0, card.abilities[0])
        self.assertEqual(4, len(self.gs.pending_choice.get_actions()))  # 3 artifacts & finish action
        select_aladdins_lamp = next(a for a in self.gs.pending_choice.get_actions()
                                    if a.description.startswith('Move ALADDIN'))
        self.gs.choice_mgr.choose(select_aladdins_lamp)
        select_colossus = next(a for a in self.gs.pending_choice.get_actions()
                               if a.description.startswith('Move COLOSSUS'))
        self.gs.choice_mgr.choose(select_colossus)
        finish_action = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(finish_action)
        self.assertEqual([colossus, aladdins_lamp], self.gs.pile_mgr.libraries[0][:2])
        self.assertFalse(self.gs.pending_choice)

    def test_dragon_engine(self):
        """{2}: This creature gets +1/+0 until end of turn."""

    def test_dragon_whelp(self):
        """{R}: DW gets +1/+0 until end of turn. If this ability has been activated > 3x EOT, sac DW at end step"""

    def test_drain_life(self):
        """Spend only black mana on X (at large).
        Drain Life deals X damage to any target. You gain life equal to the damage dealt, but not more life than:
        the player's life total before the damage was dealt (if you targeted a player) or,
        the creature's toughness (if you targeted a creature)."""
        card_1 = self.g.hand('drain-life')
        card_2 = self.g.hand('drain-life')
        self.g.mana('B' * 100)

        damage_p1_pipeline = AbilityPipeline(0, self.gs, card_1, card_1.abilities[0], x_value=1, targets=[1])
        damage_p1_pipeline.advance()
        damage_p1_pipeline.resolve_ability()
        self.assertEqual([21, 19], self.gs.life)

        bears = self.g.battlefield('grizzly-bears', owner=1)  # 2/2
        damage_bears_pipe = AbilityPipeline(0, self.gs, card_2, card_2.abilities[0], x_value=4, targets=[bears])
        damage_bears_pipe.advance()
        damage_bears_pipe.resolve_ability()
        self.assertIn(bears, self.g.gy[1])
        self.assertEqual([23, 19], self.gs.life)

    def test_drain_power_simple(self):
        """Opp activates a mana ability of each land they control.
        Then that player loses all unspent mana, and you add the mana lost this way."""
        card = self.g.hand('drain-power')  # UU
        self.g.mana('UU')
        plains = self.g.battlefield('plains', owner=1)
        swamp = self.g.battlefield('swamp', owner=1)
        maze = self.g.battlefield('maze-of-ith', owner=1)

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()
        pipeline.resolve_ability()

        self.assertTrue(swamp.is_tapped)
        self.assertTrue(plains.is_tapped)
        self.assertFalse(maze.is_tapped)
        self.assertEqual(0, sum(self.gs.mana_pools[1].available_mana.values()))
        self.assertEqual({'B': 1, 'W': 1}, {k: v for k, v in self.gs.mana_pools[0].available_mana.items() if v})

    def test_drain_power_multi_lands(self):
        """Opp activates a mana ability of each land they control.
        (If it produces multiple mana types, opp chooses which mana.)
        Then that player loses all unspent mana, and you add the mana lost this way."""
        card = self.g.hand('drain-power')  # UU
        self.g.mana('UU')
        plains = self.g.battlefield('plains', owner=1)
        swamp = self.g.battlefield('swamp', owner=1)
        volcanic_island = self.g.battlefield('volcanic-island', owner=1)  # produces ['R', 'U']
        random_spell = self.g.hand('holy-day', owner=1)  # W

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()

        # in response to drain-power, opponent uses up some of their mana
        cast_random_spell = AbilityPipeline(1, self.gs, random_spell, random_spell.abilities[0])
        cast_random_spell.advance()
        cast_random_spell.resolve_ability()

        pipeline.resolve_ability()
        volcanic_produces_red = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(volcanic_produces_red)

        self.assertTrue(swamp.is_tapped)
        self.assertTrue(volcanic_island.is_tapped)
        self.assertEqual(0, sum(self.gs.mana_pools[1].available_mana.values()))
        self.assertEqual({'B': 1, 'R': 1}, {k: v for k, v in self.gs.mana_pools[0].available_mana.values() if v})

    def test_dream_coat(self):
        """{0}: Host becomes the color or colors of your choice. Activate only once each turn."""

    def test_drop_of_honey(self):
        """At your upkeep, destroy the creature with the least power w/o regen.
        If two or more creatures are tied for least power, you choose one of them.
        When there are no creatures on the battlefield, sac DOH"""

    def test_drowned(self):
        """{B}: Regenerate this creature."""

    def test_drudge_skeletons(self):
        """{B}: Regenerate this creature
        (The next time DS would be destroyed EOT, instead tap it, remove it from combat, and heal all damage on it.)"""

    def test_dust_to_dust(self):
        """Exile two target artifacts."""

    def test_dwarven_demolition_team(self):
        """{T}: Destroy target Wall."""

    def test_dwarven_song(self):
        """One or more target creatures become red until end of turn."""

    def test_dwarven_warriors(self):
        """{T}: Target creature with power 2 or less can't be blocked this turn"""
        card = self.g.battlefield('dwarven-warriors')
        aa = card.activated_abilities[0]
        attacker = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        blocker = self.g.battlefield('grizzly-bears', owner=1)

        self.g.next_turn()
        self.g.activate_ability(aa, attacker)
        self.assertFalse(self.gs.perm_querier.can_block(blocker, attacker))

    def test_dwarven_weaponsmith(self):
        """{T}, Sacrifice an artifact: Put a +1/+1 counter on target creature. Activate only during your upkeep."""

    def test_earthbind(self):
        """When E ETB, if host has flying, E deals 2 damage to host and E gains 'Host loses flying.'"""

    def test_earthquake(self):
        """Earthquake deals X damage to each creature without flying and each player."""

    def test_eater_of_the_dead(self):
        """{0}: If this creature is tapped, exile target creature card from a graveyard and untap this creature."""

    def test_ebony_horse(self):
        """Untap target attacking creature you control.
        Prevent all combat damage that would be dealt to and dealt by that creature EOT."""

    def test_el_hajjaj(self):
        """Whenever this creature deals damage, you gain that much life."""

    def test_elder_land_wurm(self):
        """Defender, trample When this creature blocks, it loses defender."""

    def test_elder_spawn(self):
        """At your upkeep, unless you sac an Island, sac ES & it deals 6 damage to you. Red creatures can't block ES"""

    def test_electric_eel(self):
        """When EE ETB, it deals 1 damage to you. {RR}: EE gets +2/+0 EOT and deals 1 damage to you."""

    def test_elephant_graveyard(self):
        """{T}: Add {C}. {T}: Regenerate target Elephant."""

    def test_elven_riders(self):
        """This creature can't be blocked except by Walls and/or creatures with flying."""

    def test_elves_of_deep_shadow(self):
        """{T}: Add {B}. This creature deals 1 damage to you."""

    def test_emerald_dragonfly(self):
        """Flying {GG}: This creature gains first strike until end of turn."""

    def test_enchanted_being(self):
        """"Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
        card = self.g.battlefield('enchanted-being')  # 2/2
        attacker = self.g.battlefield('craw-wurm', owner=1)  # 6/4
        aura = self.g.hand('holy-strength', owner=1)
        self.g.cast_and_accept(aura, attacker, card.abilities[0], owner=1)
        self.assertTrue(attacker is aura.host)

        self.g.next_turn()
        self.g.combat(attacker, card)
        self.assertIn(card, self.gs.pile_mgr.boards[0])

    def test_enchantment_alteration(self):
        """Attach target Aura attached to a creature or land to another permanent of that type"""
        card = self.g.hand('enchantment-alteration')
        aura = self.g.hand('holy-strength')
        original_host = self.g.battlefield('grizzly-bears')  # 2/2
        self.g.cast_and_accept(aura, original_host, aura.abilities[0])

        illegal_host = self.g.battlefield('island')
        self.assertNotIn(illegal_host, card.abilities[0].target_spec.get_targets(self.gs, card))

        self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.cast_and_accept(card, aura, card.abilities[0])
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))

    def test_energy_flux(self):
        """All artifacts have 'At your upkeep, sacrifice this artifact unless you pay {2}.'"""

    def test_energy_tap(self):
        """Tap target untapped creature you control to add an amount of {C} equal to that creature's mana value."""
        card = self.g.card('energy-tap')
        self.g.mana('U')
        target = self.g.battlefield('grizzly-bears')  # MV = 2
        self.g.cast_and_accept(card, target, card.abilities[0], add_lots_of_mana=False)
        self.assertEqual(2, self.gs.mana_pools[0].available_mana.get('C'))

    def test_erg_raiders(self):
        """At your end step, if ER didn't attack, it deals you 2 damage unless it came under your control this turn."""

    def test_erhnam_djinn(self):
        """At your upkeep, target opp non-Wall gains forestwalk until your next upkeep"""

    def test_erosion(self):
        """At host's upkeep, destroy that land unless that player pays {1} or 1 life."""

    def test_eternal_flame(self):
        """EF deals X damage to opp and roundup(X/2) to you; X = Mountains you control."""

    def test_eternal_warrior(self):
        """Enchant creature Enchanted creature has vigilance."""

    def test_eureka(self):
        """Both players may take any permanent in their hand and put it directly into play.
        Players take turns playing one card from their hand until neither wants to play more permanents.
        No other spells/effects may be used while E is in effect. If a spell has an X in casting cost, X=0."""
        [h.clear() for h in self.gs.hands]
        card = self.g.hand('eureka')
        p0c1 = self.g.hand('merfolk-of-the-pearl-trident')
        self.g.hand('aladdins-lamp')
        self.g.hand('winter-orb', owner=1)
        p1c2 = self.g.hand('grizzly-bears', owner=1)
        self.g.cast_and_accept(card, None, card.abilities[0])

        merfolk_to_board = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(merfolk_to_board)
        self.assertIn(p0c1, self.gs.boards[0])

        grizzly_bears_to_board = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(grizzly_bears_to_board)
        self.assertIn(p1c2, self.gs.boards[1])

        p0_finish_playing = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(p0_finish_playing)
        p1_finish_playing = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(p1_finish_playing)
        self.assertFalse(self.gs.pending_choice)

    def test_evil_eye_of_orms_by_gore(self):
        """Non-Eye creatures you control can't attack. This creature can't be blocked except by Walls."""

    def test_evil_presence(self):
        """Enchant land Enchanted land is a Swamp."""

    def test_exorcist(self):
        """{1W}, {T}: Destroy target black creature."""

    def test_eye_for_an_eye(self):
        """The next time a source of your choice would deal damage to you this turn,
        instead that source deals that much damage to you and EYAE deals that much damage to that source's controller"""
        card = self.g.hand('eye-for-an-eye')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        self.g.next_turn(True)
        self.g.cast_and_accept(card, attacker, card.abilities[0])
        self.g.combat(attacker, None)
        self.assertEqual([18, 18], self.gs.life)

    def test_fallen_angel(self):
        """Flying Sacrifice a creature: This creature gets +2/+1 until end of turn."""

    def test_falling_star(self):
        """Flip FS onto the playing area from >= 1 ft. FS deals 3 damage to each creature it lands on.
        Tap all creatures dealt damage by FS. If FS doesn't turn completely over at least once, it has no effect."""

    def test_false_orders(self):
        """Cast this spell only during the declare blockers step.
        Remove target creature defending player controls from combat.
        Creatures it was blocking that had become blocked by only that creature this combat become unblocked.
        You may have it block an attacking creature of your choice."""

    def test_farmstead(self):
        """Host has 'At your upkeep, you may pay {WW} to gain 1 life.'"""

    def test_fastbond(self):
        """You may play any number of lands on each of your turns.
        For any land after the first in a turn, F deals 1 damage to you."""
        [h.clear() for h in self.gs.hands]
        self.g.mana('G')
        f1 = self.g.hand('forest')
        f2 = self.g.hand('forest')
        card = self.g.hand('fastbond')

        print('Next turn')
        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        self.g.cast_and_accept(card, eff_spec=card.abilities[0], add_lots_of_mana=False)
        pass_priority = self.gs.get_available_actions(0)[0]
        pass_priority.play()
        print('I played the Fastbond')

        play_f1 = self.gs.get_available_actions(0)[1]
        play_f1.play()

        # I'm not sure .play() is correct ... that doesn't allow P0 to play any more cards that turn and passes turn

        self.assertEqual(0, self.gs.player_turn_idx)
        self.assertEqual(0, self.gs.action_on_idx)

        print('A', self.gs.action_on_idx, self.gs.get_available_actions(0))
        print(self.gs.boards[0])
        print(self.gs.get_available_actions(0))
        raise ValueError()

    def test_fasting(self):
        """At your upkeep, put a hunger counter on F. Destroy F if it has >=5 hunger counters.
        If you would begin your draw step, you may skip that step instead to gain 2 life.
        When you draw a card, destroy F."""
        card = self.g.battlefield('fasting')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertEqual(1, card.counters.get_count(HUNGER))
        skip_draw_gain_life = self.gs.pending_choice.get_actions()[0]
        skip_draw_gain_life.play()

        self.g.next_turn()
        self.assertEqual(7, len(self.gs.pile_mgr.hands[0]))
        self.assertEqual(22, self.gs.life[0])

        self.gs.event_mgr.emit(UpkeepEvent(0))
        do_not_skip_draw = self.gs.pending_choice.get_actions()[1]
        do_not_skip_draw.play()
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        self.assertEqual(8, len(self.gs.pile_mgr.hands[0]))
        self.assertIn(card, self.g.gy[0])

    def test_fear(self):
        """Host has fear (It can't be blocked except by artifact creatures and/or black creatures.)"""

    def test_feedback(self):
        """At host's upkeep, F deals 1 damage to that player."""

    def test_feint(self):
        """Tap all creatures blocking target attacking creature.
        Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""

    def test_feldons_cane(self):
        """Shuffle your graveyard into your library"""
        card = self.g.battlefield('feldons-cane')
        aa = card.activated_abilities[0]
        gy1 = self.g.graveyard('lightning-bolt')
        gy2 = self.g.graveyard('ball-lightning')
        self.gs.pile_mgr.libraries[0].clear()
        self.g.activate_ability(aa)
        self.assertIn(gy1, self.gs.pile_mgr.libraries[0])
        self.assertEqual(0, len(self.g.gy[0]))

    def test_fellwar_stone_1(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('plains', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)  # type: ignore
        self.assertEqual(1, len(self.gs.pending_choice.get_actions()))

    def test_fellwar_stone_2(self):
        """{T}: Add one mana of any color that a land an opponent controls could produce"""
        fellwar_stone = self.g.battlefield('fellwar-stone')
        self.g.battlefield('birds-of-paradise', owner=1)
        fellwar_stone.activated_abilities[0].eff_spec.effect.resolve(self.gs, fellwar_stone, None)  # type: ignore
        self.assertEqual(5, len(self.gs.pending_choice.get_actions()))

    def test_festival(self):
        """Cast this spell only during an opponent's upkeep. Creatures can't attack this turn."""
        card = self.g.hand('festival')
        self.g.mana('WWWW')
        self.assertNotIn(card, [a.source for a in self.gs.available_actions_from_hand()
                                if isinstance(a, AbilityPipeline)])
        attacker = self.g.battlefield('grizzly-bears', owner=1)
        self.g.next_turn(True)

        self.g.cast_and_accept(card, None, card.abilities[0])
        self.assertFalse(self.gs.perm_querier.can_attack(attacker))

    def test_field_of_dreams(self):
        """Players play with the top card of their libraries revealed"""
        card = self.g.battlefield('field-of-dreams')
        self.g.resolve_spell(card)
        top_card = self.gs.pile_mgr.libraries[0][0]
        self.assertTrue(top_card.is_face_up)
        self.gs.pile_mgr.draw(0)
        top_card = self.gs.pile_mgr.libraries[0][0]
        self.assertTrue(top_card.is_face_up)

    def test_fire_and_brimstone(self):
        """Fire and Brimstone deals 4 damage to target player who attacked this turn and 4 damage to you."""

    def test_fire_drake(self):
        """Flying {R}: This creature gets +1/+0 until end of turn. Activate only once each turn."""

    def test_fire_sprites(self):
        """Flying {G}, {T}: Add {R}."""

    def test_fireball_one_target(self):
        """This spell costs {1} more to cast for each target beyond the first.
        F deals X damage divided evenly, rounded down, among any number of targets."""
        card = self.g.hand('fireball')  # XR
        self.g.mana('RRR')
        bears = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=2, targets=[bears])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(bears, self.g.gy[1])

    def test_fireball_multi_target(self):
        """This spell costs {1} more to cast for each target beyond the first.
        F deals X damage divided evenly, rounded down, among any number of targets."""
        card = self.g.hand('fireball')  # XR
        self.g.mana('R' * 6)
        bears = self.g.battlefield('grizzly-bears', owner=1)  # 2/2
        lions = self.g.battlefield('savannah-lions', owner=1)  # 2/1

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=4, targets=[bears, lions])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(lions, self.g.gy[1])
        self.assertIn(bears, self.g.gy[1])
        self.assertEqual(0, len(self.gs.card_filter.on_player_board(0).untapped().mountains().result()))

    def test_fireball_couldnt_pay_the_1_extra(self):
        """This spell costs {1} more to cast for each target beyond the first.
        F deals X damage divided evenly, rounded down, among any number of targets."""
        # Casting uses the R and x=4, tapping all lands; since there is no mana to pay the extra {1}; spell fizzles
        card = self.g.hand('fireball')  # XR
        self.g.mana('R' * 5)
        bears = self.g.battlefield('grizzly-bears', owner=1)  # 2/2
        lions = self.g.battlefield('savannah-lions', owner=1)  # 2/1

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=4, targets=[bears, lions])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertNotIn(lions, self.g.gy[1])
        self.assertNotIn(bears, self.g.gy[1])
        self.assertEqual(0, len(self.gs.card_filter.on_player_board(0).untapped().mountains().result()))

    def test_firebreathing(self):
        """Enchant creature {R}: Enchanted creature gets +1/+0 until end of turn."""

    def test_firestorm_phoenix(self):
        """If this card would die, bounce it instead; it cannot be re-summoned this turn"""
        self.gs.hands[0].clear()
        card = self.g.battlefield('firestorm-phoenix')  # 3/2
        bolt = self.g.hand('lightning-bolt')
        self.g.mana('RRRRRRRRRRRRR')
        self.g.cast_and_accept(bolt, card, bolt.abilities[0])
        self.assertIn(card, self.gs.hands[0])
        self.assertFalse(any(a.source is card for a in self.gs.available_actions_from_hand()))

        self.g.next_turn()
        self.assertTrue(any(a.source is card for a in self.gs.available_actions_from_hand()))

    def test_fishliver_oil(self):
        """Host has islandwalk"""

    def test_fissure(self):
        """Destroy target creature or land. It can't be regenerated."""

    def test_flash_counter(self):
        """Counter target instant spell."""

    def test_flash_flood(self):
        """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""

    def test_flashfires(self):
        """Destroy all Plains."""

    def test_flight(self):
        """Enchant creature Enchanted creature has flying."""

    def test_flood(self):
        """{UU}: Tap target creature without flying."""

    def test_floral_spuzzem(self):
        """Whenever FS attacks & isn't blocked, you may destroy target opp artifact & FS assigns no combat damage EOT"""

    def test_flying_carpet(self):
        """{2}, {T}: Target creature gains flying until end of turn."""

    def test_fog(self):
        """Prevent all combat damage this turn"""
        card = self.g.hand('fog')
        attacker = self.g.battlefield('grizzly-bears', owner=1)  # 2/2
        bolt = self.g.hand('lightning-bolt', owner=1)

        self.g.next_turn(True)
        self.g.cast_and_accept(card, None, card.abilities[0])
        self.assertTrue(self.g.card_has_a_registered_listener(card))
        self.g.combat(attacker, None)
        self.assertEqual(20, self.gs.life[0])

        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.assertEqual(17, self.gs.life[0])  # doesn't prevent non-combat damage

        self.g.next_turn()
        self.g.combat(attacker, None)
        self.assertEqual(15, self.gs.life[0])  # effect wears off EOT

    def test_force_of_nature(self):
        """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
        self.g.battlefield('force-of-nature')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(12, self.gs.life[0])

        self.g.mana('GGGGG')  # five forests
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        pay_gggg = self.gs.pending_choice.get_actions()[0]
        pay_gggg.play()
        self.assertEqual(1, len([c for c in self.gs.pile_mgr.boards[0]
                                 if c.props.slug == 'forest' and not c.is_tapped]))

    def test_force_spike_1(self):
        """Counter target spell unless its controller pays {1} ... This is the counter test"""
        card = self.g.hand('force-spike')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('U')
        self.g.mana('RR', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()
        self.assertIn(bolt_pipeline, [a.pipeline for a in self.gs.action_stack.actions if isinstance(a, AbilityAction)])
        bolt_stack_action = next(a for a in self.gs.action_stack.actions)

        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[bolt_stack_action])
        card_pipeline.advance()
        card_pipeline.resolve_ability()
        allow_bolt_countered = self.gs.pending_choice.get_actions()[1]
        allow_bolt_countered.play()
        self.assertTrue(20, self.gs.life[1])
        self.assertTrue(self.gs.pending_choice is None)

    def test_force_spike_2(self):
        """Counter target spell unless its controller pays {1} ... This is the pay mana test"""
        card = self.g.hand('force-spike')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('U')
        self.g.mana('RR', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()
        self.assertIn(bolt_pipeline, [a.pipeline for a in self.gs.action_stack.actions if isinstance(a, AbilityAction)])
        bolt_stack_action = next(a for a in self.gs.action_stack.actions)

        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[bolt_stack_action])
        card_pipeline.advance()
        card_pipeline.resolve_ability()
        pay_mana_to_prevent_counter = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_mana_to_prevent_counter)

        # Force Spike is gone; Lightning Bolt remains.
        self.assertTrue(any(a.source is bolt for a in self.gs.action_stack.actions))
        self.assertFalse(any(a.source is card for a in self.gs.action_stack.actions))

        # Both players pass priority.
        self.gs.get_available_actions(self.gs.action_on_idx)[0].play()
        self.gs.get_available_actions(self.gs.action_on_idx)[0].play()

        self.assertEqual(17, self.gs.life[0])
        self.assertIsNone(self.gs.pending_choice)

    def test_forcefield(self):
        """{1}: The next time an unblocked creature of your choice would deal combat damage to you this turn,
        prevent all but 1 of that damage"""
        ff = self.g.battlefield('forcefield', owner=1)
        self.g.mana('U', owner=1)
        attacker = self.g.battlefield('grizzly-bears')  # 2/2
        self.gs.combat_mgr.create_combat(attacker)
        self.g.activate_ability(ff.activated_abilities[0], attacker, 1)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertEqual(19, self.gs.life[1])

    def test_forethought_amulet(self):
        """At your upkeep, pay {3} or sac FA. If an instant or sorcery source would deal >=3 damage to you,
        it deals 2 damage to you instead."""
        card = self.g.battlefield('forethought-amulet')
        self.g.mana('UUUUUUUU')
        self.gs.event_mgr.emit(UpkeepEvent(0))
        pay_mana = self.gs.pending_choice.get_actions()[0]
        pay_mana.play()

        self.g.next_turn(True)
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.cast_and_accept(bolt, 0, bolt.abilities[0], owner=1)
        self.assertEqual(18, self.gs.life[0])

        self.g.next_turn(True)
        self.gs.event_mgr.emit(UpkeepEvent(0))
        sac_fa = self.gs.pending_choice.get_actions()[1]
        sac_fa.play()
        self.assertIn(card, self.g.gy[0])

    def test_fountain_of_youth(self):
        """{2}, {T}: You gain 1 life."""

    def test_frankensteins_monster(self):
        """As FM enters, exile X creatures from your gy. If you can't, put FM into in gy instead of battlefield. X >= 0.
        For each creature card exiled this way, this creature enters with a +2/+0, +1/+1, or +0/+2 counter on it."""
        card = self.g.hand('frankensteins-monster')  # 0/1
        c1 = self.g.graveyard('savannah-lions')
        c2 = self.g.graveyard('tundra-wolves')
        self.g.mana('BBBB')

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=2)
        pipeline.advance()
        pipeline.resolve_ability()

        reanimate_c1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(reanimate_c1)
        add_0_2 = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(add_0_2)
        reanimate_c2 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(reanimate_c2)
        add_1_1 = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(add_1_1)

        self.assertIn(c1, self.gs.boards[0])
        self.assertIn(c2, self.gs.boards[0])
        self.assertEqual((1, 4), (card.power, card.toughness))
        self.assertIsNone(self.gs.pending_choice)

    def test_frankensteins_monster_x_eq_0(self):
        """As FM enters, exile X creatures from your gy. If you can't, put FM into in gy instead of battlefield. X >= 0.
        For each creature card exiled this way, this creature enters with a +2/+0, +1/+1, or +0/+2 counter on it."""
        card = self.g.hand('frankensteins-monster')  # 0/1
        self.g.mana('BB')

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=0)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual((0, 1), (card.power, card.toughness))
        self.assertIn(card, self.gs.boards[0])

    def test_frankensteins_monster_cant_exile_x(self):
        """As FM enters, exile X creatures from your gy. If you can't, put FM into in gy instead of battlefield ... """
        card = self.g.hand('frankensteins-monster')  # 0/1
        self.g.mana('BBBB')

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=2)
        pipeline.advance()
        pipeline.resolve_ability()

        print(len(self.g.gy[0]), pipeline.x_value, card.zone)
        self.assertIn(card, self.g.gy[0],
                      "AP.resolve_ability() happens after .resolve() & moves FM from gy to board")

    def test_frozen_shade(self):
        """{B}: This creature gets +1/+1 until end of turn."""

    def test_fungusaur(self):
        """Whenever this creature is dealt damage, put a +1/+1 counter on it."""


if __name__ == '__main__':
    unittest.main()

