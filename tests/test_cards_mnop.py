import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import SelectXAction2
from models.actions.cast import CastWithNoSpellEffect
from models.actions.advance_phase import PassTheTurn
from models.constants import KW
from models.cost import ExileCardCost, SacCardCost
from models.effects.base import ActivatedAbility
from models.game_card.counter_tokens import PLUS_ONE
from models.events_all import UpkeepEvent, StateBasedEvent, EndStepEvent, DrawStepEvent
from models.systems.phase import Phase
from tests.setup_helpers import TestGame

class TestCardsMNOP(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_magnetic_mountain(self):
        """Blue creatures don't untap during their controllers' untap steps.
        At each player's upkeep, that player may choose any # of their tapped blue creatures & pay {4} to untap it."""
        self.g.battlefield('magnetic-mountain')
        blue1 = self.g.battlefield('serendib-efreet')
        blue2 = self.g.battlefield('merfolk-of-the-pearl-trident')
        non_blue = self.g.battlefield('grizzly-bears')
        self.g.mana('UUUUUUUU')
        blue1.tap()
        blue2.tap()
        non_blue.tap()

        self.g.next_turn()
        self.assertTrue(blue1.is_tapped)
        self.assertFalse(non_blue.is_tapped)

        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        first_blue_untap = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(first_blue_untap)
        self.assertFalse(blue1.is_tapped)

        dont_untap_anymore = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(dont_untap_anymore)
        self.assertTrue(blue2.is_tapped)
        self.assertFalse(self.gs.pending_choice)

    def test_mana_clash(self):
        """You and target opponent each flip a coin. MC deals 1 damage to each player whose coin comes up tails.
        Repeat this process until both players' coins come up heads on the same flip."""

    def test_mana_drain(self):
        """Counter target spell. At your next main phase, add an amount of {C} equal to that spell's mana value."""

    def test_mana_flare(self):
        """Whenever a player taps a land for mana, it produces one additional mana of the same type."""
        self.g.battlefield('mana-flare')
        holy_day = self.g.hand('holy-day')
        self.g.mana('W')

        # a land is tapped for mana
        pipeline = AbilityPipeline(0, self.gs, holy_day, holy_day.abilities[0])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(1, self.gs.mana_pools[0].available_mana['W'])

        # a land tapped but not for mana
        land = self.g.battlefield('island')
        land.tap()
        self.assertEqual(0, self.gs.mana_pools[0].available_mana['U'])

    def test_mana_matrix(self):
        """Instant and enchantment spells you cast cost {2} less to cast."""

    def test_mana_short(self):
        """Tap all lands target player controls and that player loses all unspent mana."""

    def test_mana_vault(self):
        """... MV doesn't untap during your untap step. At your upkeep, you may pay {4} to untap this artifact.
        At your draw step, if this artifact is tapped, it deals 1 damage to you ..."""
        card = self.g.battlefield('mana-vault')
        card.tap()
        self.g.mana('RRRR')

        self.g.next_turn()
        self.assertTrue(card.is_tapped)
        self.gs.event_mgr.emit(DrawStepEvent(0))
        self.assertTrue(19, self.gs.life[0])

        self.gs.event_mgr.emit(UpkeepEvent(0))
        pay_to_untap = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(pay_to_untap)
        self.assertFalse(card.is_tapped)

    def test_mana_vortex(self):
        """When you cast MV, counter it unless you sacrifice a land.
        At each player's upkeep, that player sacs a land of their choice.
        When there are no lands on the battlefield, sac MV."""
        card = self.g.hand('mana-vortex')
        island_to_sac = self.g.battlefield('island')
        self.g.cast_and_accept(card, island_to_sac, card.abilities[0])
        self.assertIn(island_to_sac, self.g.gy[0])

        opp_land = self.g.battlefield('swamp', owner=1)
        for my_land in self.gs.card_filter.on_player_board(0).lands().result()[::]:
            self.gs.pile_mgr.destroy(my_land)
        print('Total Lands in play', len(self.gs.card_filter.in_play().lands().result()))

        self.g.next_turn(True)
        self.gs.event_mgr.emit(UpkeepEvent(0))
        self.assertIn(opp_land, self.g.gy[1])
        self.gs.event_mgr.emit(StateBasedEvent())
        self.assertIn(card, self.g.gy[0])

    def test_manabarbs(self):
        """Whenever a player taps a land for mana, M deals 1 damage to that player"""
        self.g.battlefield('manabarbs')
        holy_day = self.g.hand('holy-day')
        self.g.mana('W')

        # a land is tapped for mana
        pipeline = AbilityPipeline(0, self.gs, holy_day, holy_day.abilities[0])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(19, self.gs.life[0])

        # a land tapped but not for mana
        land = self.g.battlefield('island')
        land.tap()
        self.assertEqual(19, self.gs.life[0])

    def test_marble_priest(self):
        """All Walls able to block this creature do so. Prevent all combat damage that would be dealt to MP by Walls."""

    def test_marsh_gas(self):
        """All creatures get -2/-0 until end of turn."""

    def test_marsh_viper(self):
        """Whenever MV deals damage to a player, that player gets two poison counters. (>= 10 poison = a loss)"""

    def test_martyrs_cry(self):
        """Exile all white creatures. For each creature exiled this way, its controller draws a card."""

    def test_martyrs_of_korlis(self):
        """As long as MOK is untapped, all damage that would be dealt to you by artifacts is dealt to MOK instead"""
        card = self.g.battlefield('martyrs-of-korlis')  # 1/6
        attacker = self.g.battlefield('colossus-of-sardia', owner=1)  # 9/9

        self.g.next_turn(True)
        card.tap()
        self.g.combat(attacker, None)
        self.assertEqual(11, self.gs.life[0])

        self.g.next_turn()
        card.untap()
        self.g.combat(attacker, None)
        self.assertEqual(11, self.gs.life[0])
        self.assertIn(card, self.g.gy[0])

    def test_maze_of_ith(self):
        """{T}: Untap target attacker. Prevent all combat damage that would be dealt to and  by that creature EOT."""
        card = self.g.battlefield('maze-of-ith')
        aa = card.activated_abilities[0]
        attacker = self.g.battlefield('shivan-dragon', owner=1)

        self.g.next_turn(True)
        self.gs.combat_mgr.create_combat(attacker)
        self.g.activate_ability(aa, attacker)
        self.gs.combat_mgr.handle_damage_step(False)
        self.assertFalse(attacker.is_tapped)
        self.assertEqual(20, self.gs.life[0])

    def test_meekstone(self):
        """Creatures with power 3 or greater don't untap during their controllers' untap steps."""

    def test_merchant_ship(self):
        """Islandhome. Whenever this creature attacks and isn't blocked, you gain 2 life."""

    def test_merfolk_assassin(self):
        """{T}: Destroy target creature with islandwalk."""

    def test_metamorphosis(self):
        """As an additional cost to cast this spell, sac a creature.
        Add X mana of any one color, X = 1 + sac'ed creature's MV.
        Spend this mana only to cast creature spells. <- This part is at large"""
        card = self.g.hand('metamorphosis')
        self.g.mana('G')
        sac_target = self.g.battlefield('tundra-wolves')  # MV=1

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0],
                                   selected_extra_costs=[SacCardCost(selected_card=sac_target)])
        pipeline.advance()
        pipeline.resolve_ability()
        add_mana = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(add_mana)
        self.assertEqual(2, sum(self.gs.mana_pools[0].available_mana.values()))

    def test_mightstone(self):
        """Attacking creatures get +1/+0."""

    def test_mijae_djinn(self):
        """Whenever MD attacks, flip a coin. If you lose the flip, remove this creature from combat and tap it."""

    def test_millstone(self):
        """{2}, {T}: Target player mills two cards."""

    def test_mind_bomb(self):
        """Each player may discard <= 3 cards. MB deals damage to each player = 3 - card count discarded this way."""
        self.gs.pile_mgr.hands[0].clear()
        card = self.g.hand('mind-bomb')
        self.g.cast_and_accept(card, eff_spec=card.abilities[0])

        # Hand card count: [0, 7]
        discard_card = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(discard_card)
        discard_card = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(discard_card)
        finish_discarding = self.gs.pending_choice.get_actions()[-1]
        self.gs.choice_mgr.choose(finish_discarding)

        self.assertEqual(5, len(self.gs.hands[1]))
        self.assertEqual([17, 19], self.gs.life)

    def test_mind_twist(self):
        """Target player discards X cards at random."""

    def test_miracle_worker(self):
        """{T}: Destroy target Aura attached to a creature you control."""

    def test_mirror_universe(self):
        """{T}, Sacrifice this artifact: Exchange life totals with target opponent. Activate only during your upkeep."""
        card = self.g.battlefield('mirror-universe')
        aa = card.activated_abilities[0]
        self.gs.apply_damage(card, 1, 1)  # life = [20, 19]
        self.g.activate_ability(aa)
        self.assertIn(card, self.g.gy[0])
        self.assertEqual([19, 20], self.gs.life)

    def test_mishras_factory(self):
        """{T}: Add {C}.
        {1}: MF becomes a 2/2 Assembly-Worker artifact creature EOT. It's still a land.
        {T}: Target Assembly-Worker creature gets +1/+1 EOT."""

    def test_mishras_workshop(self):
        """{T}: Add {CCC}. Spend this mana only to cast artifact spells."""

    def test_moat(self):
        """Creatures without flying can't attack."""

    def test_mold_demon(self):
        """When this creature enters, sacrifice it unless you sacrifice two Swamps"""
        card = self.g.card('mold-demon')
        self.g.battlefield('swamp', cnt=9)
        self.g.cast_and_accept(card, None, card.abilities[0])
        swamp_cnt_before = len(self.gs.card_filter.on_player_board(0).swamps().result())
        sac_two_swamps = self.gs.pending_choice.get_actions()[0]
        sac_two_swamps.play()
        swamp_cnt_after = len(self.gs.card_filter.on_player_board(0).swamps().result())
        self.assertEqual(2, swamp_cnt_before - swamp_cnt_after)

    def test_morale(self):
        """Attacking creatures get +1/+1 until end of turn."""

    def test_mox_emerald(self):
        """{T}: Add {G}."""

    def test_mox_jet(self):
        """{T}: Add {B}."""

    def test_mox_pearl(self):
        """{T}: Add {W}."""

    def test_mox_ruby(self):
        """{T}: Add {R}."""

    def test_mox_sapphire(self):
        """{T}: Add {U}."""

    def test_murk_dwellers(self):
        """Whenever this creature attacks and isn't blocked, it gets +2/+0 until end of combat."""

    def test_nafs_asp_pays_path(self):
        """Whenever NA deals damage to opp, at any point up to opp's next draw phase, opp pays {1} or loses 1 life"""
        [h.clear() for h in self.gs.hands]
        card = self.g.battlefield('nafs-asp')  # 1/1
        plains = self.g.battlefield('plains', owner=1)

        self.gs.phase_mgr.set_phase(Phase.MAIN)
        self.g.combat(card, None)
        self.assertEqual(19, self.gs.life[1])

        emblem = self.gs.emblem_mgr.emblems[0]
        pipeline = AbilityPipeline(1, self.gs, card, emblem.eff_spec, is_emblem=True)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertTrue(plains.is_tapped)

        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        self.assertEqual(19, self.gs.life[1])

    def test_nafs_asp_unpaid_path(self):
        """Whenever NA deals damage to opp, at any point up to opp's next draw phase, opp pays {1} or loses 1 life"""
        [h.clear() for h in self.gs.hands]
        card = self.g.battlefield('nafs-asp')  # 1/1

        self.gs.phase_mgr.set_phase(Phase.MAIN)
        self.g.combat(card, None)
        self.assertEqual(19, self.gs.life[1])

        self.g.next_turn(True)
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        self.assertEqual(18, self.gs.life[1])
        self.assertEqual(0, len(self.gs.emblem_mgr.emblems))

    def test_nameless_race(self):
        """As NR ETB, pay any amount of life <=
        the count of white nontoken permanents your opponents control + count of white cards in their graveyards.
        NR's power and toughness are each equal to the life paid as it entered."""

    def test_natural_selection(self):
        """Look at the top 3 cards of target player's library, then put them back in any order.
        You may have that player shuffle."""

    def test_nebuchadnezzar(self):
        """{X}, {T}: Choose a card name. Opp reveals X cards at random from their hand.
        Then that player discards all cards with that name revealed this way."""
        self.gs.hands[1].clear()
        island = self.g.hand('island', owner=1)
        swamp1 = self.g.hand('swamp', owner=1)
        swamp2 = self.g.hand('swamp', owner=1)
        card = self.g.battlefield('nebuchadnezzar')
        aa = card.activated_abilities[0]
        self.g.mana('BBB')

        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, x_value=3)
        pipeline.advance()
        pipeline.resolve_ability()

        name_swamp = next(a for a in self.gs.pending_choice.get_actions() if a.description == 'Name Swamp')
        self.gs.choice_mgr.choose(name_swamp)
        self.assertIn(swamp1, self.g.gy[1])
        self.assertIn(swamp2, self.g.gy[1])
        self.assertIn(island, self.gs.hands[1])

        self.g.next_turn()
        self.gs.hands[1].clear()
        island = self.g.hand('island', owner=1)
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, x_value=1)
        pipeline.advance()
        pipeline.resolve_ability()

        name_swamp = next(a for a in self.gs.pending_choice.get_actions() if a.description == 'Name Swamp')
        self.gs.choice_mgr.choose(name_swamp)
        self.assertIn(island, self.gs.hands[1])

    def test_necropolis(self):
        """Exile a creature card from your graveyard: Put X +0/+1 counters on this creature, X = the exiled card's MV"""
        self.g.graveyard('merfolk-of-the-pearl-trident')  # U
        air_elemental = self.g.graveyard('air-elemental')  # 3UU
        card = self.g.battlefield('necropolis')  # 0/1
        aa = card.activated_abilities[0]

        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, targets=[card])
        exile_air_elemental = ExileCardCost(selected_card=air_elemental)
        pipeline.cost_results = [exile_air_elemental.pay(self.gs, card)]
        pipeline.advance()
        pipeline.resolve_ability()

        self.assertEqual(card.toughness, 6)
        self.assertIn(air_elemental, self.gs.exiles[0])

    def test_nether_shadow(self):
        """At your upkeep, if NS is in your gy w >=3 creatures above it, you may put this card onto the battlefield"""
        # TODO: WARNING: if this card never goes to the battlefield, its Listener is never registered
        card = self.g.battlefield('nether-shadow')
        self.gs.pile_mgr.destroy(card)
        self.g.graveyard('ornithopter')
        self.g.graveyard('grizzly-bears')

        # not enough creatures above NS
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertIsNone(self.gs.pending_choice)

        # enough above NS, give owner option to reanimate
        self.g.graveyard('shivan-dragon')
        print('Dragon in gy')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        reanimate_nether_shadow = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(reanimate_nether_shadow)
        self.assertIn(card, self.gs.boards[0])

    def test_nether_void(self):
        """Whenever a player casts a spell, counter it unless that player pays {3}"""
        self.g.battlefield('nether-void')
        target1 = self.g.hand('merfolk-of-the-pearl-trident')
        self.g.mana('U')
        add_to_stack_action = CastWithNoSpellEffect(0, self.gs, target1)
        add_to_stack_action.play()
        self.assertIn(target1, self.g.gy[0])  # not enough mana to prevent nether-void counter
        self.assertFalse(len(self.gs.action_stack.actions))

        target2 = self.g.hand('lightning-bolt')
        self.g.mana('RRRR')
        ap = AbilityPipeline(0, self.gs, target2, target2.abilities[0], targets=[1])
        ap.finish()
        ap.resolve_ability()
        pay_mana_to_prevent_counter_action = self.gs.pending_choice.get_actions()[0]
        pay_mana_to_prevent_counter_action.play()

        self.assertEqual(17, self.gs.life[1])
        self.assertTrue(all(c.is_tapped for c in self.gs.card_filter.on_player_board(0).mountains().result()))

    def test_nettling_imp(self):
        """{T}: Choose target non-Wall creature the active player has controlled continuously since BOT.
        That creature attacks this turn if able. Destroy at end step if it didn't attack this turn.
        Activate only during an opponent's turn, before attackers are declared."""
        card = self.g.battlefield('nettling-imp')
        aa = card.activated_abilities[0]
        legal_target = self.g.battlefield('savannah-lions', owner=1)
        legal_target_2 = self.g.battlefield('tundra-wolves', owner=1)
        illegal_target_1 = self.g.battlefield('wall-of-brambles', owner=1)

        self.g.next_turn(True)
        illegal_target_2 = self.g.battlefield('merfolk-of-the-pearl-trident', owner=1)
        targets = aa.eff_spec.target_spec.get_targets(self.gs, card)
        self.assertIn(legal_target, targets)
        self.assertNotIn(illegal_target_1, targets)
        self.assertNotIn(illegal_target_2, targets)

        self.assertNotIn(KW.GOAD, legal_target.keyword_abilities)
        self.g.activate_ability(aa, legal_target)
        self.assertIn(KW.GOAD, legal_target.keyword_abilities)

        self.g.next_turn()
        festival = self.g.hand('festival')  # no creatures may attack
        self.g.cast_and_accept(festival, None, festival.abilities[0])
        self.g.activate_ability(aa, legal_target_2)
        self.gs.event_mgr.emit(EndStepEvent(1))
        self.assertIn(legal_target_2, self.g.gy[1])

    def test_nevinyrrals_disk(self):
        """This artifact enters tapped. {1}, {T}: Destroy all artifacts, creatures, and enchantments."""

    def test_niall_silvain(self):
        """{GGGG}, {T}: Regenerate target creature."""

    def test_nicol_bolas(self):
        """At your upkeep, sac MB unless you pay {UBR}. Whenever NB deals damage to an opp, opp discards their hand."""

    def test_nightmare(self):
        """N's power and toughness are each equal to the number of Swamps you control."""

    def test_north_star(self):
        """For 1 spell EOT, you may spend mana as though it were mana of any type to pay that spell's mana cost.
        (Additional costs are still paid normally.) (see readme.md)"""
        self.gs.hands[0].clear()
        card = self.g.battlefield('north-star')
        aa = card.activated_abilities[0]
        self.g.mana('BBBB')
        self.g.mana('R')
        wolves = self.g.hand('tundra-wolves')  # W
        bolt = self.g.hand('lightning-bolt')  # R

        self.gs.phase_mgr.set_phase(Phase.MAIN)
        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertTrue(self.g.card_has_a_registered_listener(card))

        self.gs.action_on_idx = 0
        print(self.gs.available_actions_from_hand())
        raise ValueError("Fails in GameState line 252 (self.mana_pools[self.action_on_idx].can_pay(c.casting_cost)), "
                         "which probably nevers queries for mana produced")

    def test_northern_paladin(self):
        """{WW}, {T}: Destroy target black permanent."""

    def test_nova_pentacle(self):
        """{3}, {T}: The next time a source of your choice would deal damage to you this turn,
        that damage is dealt to target creature of an opponent's choice instead"""
        [h.clear() for h in self.gs.hands]
        card = self.g.battlefield('nova-pentacle')
        aa = card.activated_abilities[0]
        self.g.mana('WWW')
        random_creature = self.g.battlefield('grizzly-bears', owner=1)
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('R', owner=1)

        self.g.next_turn(True)
        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()

        nova_pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, targets=[bolt_pipeline])
        nova_pipeline.advance()
        nova_pipeline.resolve_ability()
        self.assertTrue(self.g.card_has_a_registered_listener(card))

        # The Listener is created, listening to DamageProposedEvent ...
        # however: that event has already been emitted; we don't trigger DamageProposedEvent a second time,
        # so NovaPentacle's on_event(DamageProposedEvent) is never called ...
        # This isn't specific to this Effect its true for any Listener so ...
        # Create this test again in a generic test script

        bolt_pipeline.resolve_ability()
        self.assertIn(random_creature, self.g.gy[1])
        self.assertEqual([20, 20], self.gs.life)

        raise ValueError()

    def test_oasis(self):
        """{T}: Prevent the next 1 damage that would be dealt to target creature this turn."""

    def test_obelisk_of_undoing(self):
        """{6}, {T}: Return target permanent you both own and control to your hand"""
        card = self.g.battlefield('obelisk-of-undoing')
        aa = card.activated_abilities[0]
        self.g.mana('UUUUUUUUU')
        target = self.g.battlefield('merfolk-of-the-pearl-trident')
        self.g.activate_ability(aa, target)
        self.assertNotIn(target, self.gs.pile_mgr.boards[0])

        illegal_target = self.g.battlefield('grizzly-bears', owner=1)
        self.assertNotIn(illegal_target, aa.eff_spec.target_spec.get_targets(self.gs, card))

    def test_old_man_of_the_sea(self):
        """You may choose not to untap this creature during your untap step.
        {T}: Gain control of target creature with power <= OMOTS's power for as long as:
        this creature remains tapped and that creature's power remains <= OMOTS's power."""
        card = self.g.battlefield('old-man-of-the-sea')  # 2/3
        aa = card.activated_abilities[0]
        target = self.g.battlefield('scryb-sprites', owner=1)  # 1/1
        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)

        self.g.next_turn()
        card.untap()
        self.assertEqual(1, target.owner_id)

        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)
        pump = self.g.hand('giant-growth')
        pump.abilities[0].effect.resolve(self.gs, pump, target)

        print('---------')
        print(card.power, target.power)  # this correctly indicates that OMOTS's power is 5
        self.gs.event_mgr.emit(StateBasedEvent())
        print(card.power, target.power)  # this correctly indicates that OMOTS's power is 5
        self.assertEqual(1, target.owner_id, 'Target should have been returned to original owner when pumped')
        self.assertIn(target, self.gs.boards[1])

    def test_onulet(self):
        """When this creature dies, you gain 2 life."""

    def test_orc_general(self):
        """{T}, Sacrifice another Orc or Goblin: Other Orc creatures get +1/+1 until end of turn."""

    def test_orcish_artillery(self):
        """{T}: This creature deals 2 damage to any target and 3 damage to you"""
        card = self.g.battlefield('orcish-artillery')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertIn(target, self.g.gy[1])

        self.g.next_turn()
        self.g.activate_ability(aa, 1)
        self.assertEqual([14, 18], self.gs.life)

    def test_orcish_mechanics(self):
        """{T}, Sacrifice an artifact: This creature deals 2 damage to any target."""

    def test_orcish_oriflamme(self):
        """Attacking creatures you control get +1/+0."""

    def test_osai_vultures(self):
        """At each end step, if a creature died this turn, put a carrion counter on OV.
        Remove two carrion counters from this creature: OV gets +1/+1 until end of turn."""

    def test_palladia_mors(self):
        """Flying, trample At the beginning of your upkeep, sacrifice Palladia-Mors unless you pay {RGW}."""

    def test_paralyze(self):
        """When this Aura enters, tap host. Host doesn't untap during its untap step.
        At host's upkeep, that player may pay {4} to untap host."""
        card = self.g.battlefield('paralyze')
        host = self.g.battlefield('grizzly-bears', owner=1)
        self.g.mana('B')
        self.g.attach(card, host)
        card.abilities[2].effect.resolve(self.gs, card, host)
        self.assertTrue(host.is_tapped)

        self.g.mana('GGGG', owner=1)
        PassTheTurn(0, self.gs).play()
        self.assertTrue(host.is_tapped)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertTrue(any(a.description.startswith('Leave ') for a in self.gs.pending_choice.get_actions()))

    def test_part_water(self):
        """[casting cost XXU] X target creatures gain islandwalk until end of turn."""
        card = self.g.hand('part-water')
        c_1 = self.g.battlefield('savannah-lions')
        self.g.battlefield('serendib-efreet')
        self.g.mana('UU')

        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], x_value=1)
        self.assertFalse(pipeline.can_begin())

        self.g.mana('U')
        self.assertTrue(pipeline.can_begin())

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.targets.append(c_1)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(KW.ISLANDWALK, c_1.keyword_abilities)

    def test_pavel_maliki(self):
        """{BR}: Pavel Maliki gets +1/+0 until end of turn."""

    def test_pendelhaven(self):
        """{T}: Add {G}. {T}: Target 1/1 creature gets +1/+2 until end of turn."""
        card = self.g.battlefield('pendelhaven')
        aa = card.activated_abilities[1]
        illegal_target = self.g.battlefield('giant-spider')  # 2/4
        self.assertNotIn(illegal_target, aa.eff_spec.target_spec.get_targets(self.gs, card))

        legal_target = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        self.g.activate_ability(aa, legal_target)
        self.assertEqual((2, 3), (legal_target.power, legal_target.toughness))

    def test_people_of_the_woods(self):
        """People of the Woods's toughness is equal to the number of Forests you control."""

    def test_personal_incarnation(self):
        """{0}: The next 1 damage that would be dealt to PI this turn is dealt to its owner instead.
        When PA dies, its owner loses half their life, rounded up."""
        card = self.g.battlefield('personal-incarnation')  # 6/6
        aa = card.activated_abilities[0]
        self.g.activate_ability(aa, card)
        self.g.activate_ability(aa, card)

        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('R', owner=1)
        pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0])
        pipeline.targets.append(card)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual(1, card.damage_received_this_turn)
        self.assertEqual(18, self.gs.life[0])

    def test_pestilence(self):
        """At end step, if no creatures are on the battlefield, sac P.
        {B}: This enchantment deals 1 damage to each creature and each player."""

    def test_petra_sphinx(self):
        """{T}: Target player chooses a card name, then reveals the top card of their library.
        If that card has the chosen name, put it into their hand. If it doesn't, put it into their graveyard."""
        self.gs.pile_mgr.libraries[0].clear()
        card = self.g.battlefield('petra-sphinx')
        aa = card.activated_abilities[0]

        swamp = self.g.library('swamp')
        island = self.g.library('island')
        self.g.activate_ability(aa, 0)
        name_swamp = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(name_swamp)
        self.assertIn(island, self.g.gy[0])

        card.untap()
        self.g.activate_ability(aa, 0)
        name_swamp = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(name_swamp)
        self.assertIn(swamp, self.gs.hands[0])

    def test_phantasmal_forces(self):
        """Flying At the beginning of your upkeep, sacrifice this creature unless you pay {U}."""

    def test_phantasmal_terrain(self):
        """As this Aura enters, choose a basic land type. Host is the chosen type."""
        card = self.g.hand('phantasmal-terrain')
        target = self.g.battlefield('mountain', owner=1)
        self.g.cast_and_accept(card, target, card.abilities[0])
        convert_to_swamp = self.gs.pending_choice.get_actions()[4]
        convert_to_swamp.play()
        self.assertIn(target, self.gs.card_filter.on_player_board(1).swamps().result())

    def test_phyrexian_gremlins(self):
        """... {T}: Tap target artifact.
        It doesn't untap during its controller's untap step so long as PG remains tapped."""
        card = self.g.battlefield('phyrexian-gremlins')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('sol-ring', owner=1)
        self.g.activate_ability(aa, target)
        self.assertTrue(target.is_tapped)

        self.g.next_turn(True)
        self.assertTrue(target.is_tapped)
        card.untap()

        self.g.next_turn()
        self.assertFalse(target.is_tapped)

    def test_piety(self):
        """Blocking creatures get +0/+3 until end of turn."""

    def test_pirate_ship(self):
        """Islandhome. {T}: This creature deals 1 damage to any target."""

    def test_pit_scorpion(self):
        """Whenever PS deals damage to a player, that player gets a poison counter. (>= 10 poison counters is a loss)"""

    def test_pixie_queen(self):
        """Flying {GGG}, {T}: Target creature gains flying until end of turn."""

    def test_plague_rats(self):
        """PR's power and toughness are each equal to the number of creatures named Plague Rats on the battlefield."""

    def test_planar_gate(self):
        """Creature spells you cast cost {2} less to cast."""

    def test_plateau(self):
        """u003ciu003e({T}: Add {R} or {W}.)u003c/iu003e"""

    def test_power_artifact(self):
        """Host's activated abilities cost {2} less to activate. This effect can't reduce that cost to < one mana"""

    def test_power_leak(self):
        """At host's upkeep, PL deals 2 damage to host owner. Host may pay X mana to prevent X of that damage."""
        card = self.g.battlefield('power-leak')
        host = self.g.battlefield('grizzly-bears')
        self.g.mana('GG')
        self.g.attach(card, host)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(3, len([a for a in self.gs.pending_choice.get_actions()
                                 if a.description.startswith('Pay ')]))

    def test_power_sink_1_controller_pays_path(self):
        """Counter target spell unless its controller pays {X}.
        If opponent doesn't, they tap all lands with mana abilities they control and lose all unspent mana."""
        card = self.g.hand('power-sink')  # casting_cost = XU
        self.g.mana('UUU')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('RRR', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()
        bolt_stack_action = next(a for a in self.gs.action_stack.actions)
        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[bolt_stack_action])
        x_action = SelectXAction2(0, self.gs, card_pipeline, 2)
        x_action.play()
        card_pipeline.advance()
        card_pipeline.resolve_ability()
        pay_mana_to_prevent_counter = self.gs.pending_choice.get_actions()[0]
        pay_mana_to_prevent_counter.play()
        bolt_stack_action.play()
        self.assertEqual(17, self.gs.life[0])

    def test_power_sink_2_spell_countered_path(self):
        """Counter target spell unless its controller pays {X}.
        If opponent doesn't, they tap all lands with mana abilities they control and lose all unspent mana."""
        card = self.g.hand('power-sink')  # casting_cost = XU
        self.g.mana('UUU')
        bolt = self.g.hand('lightning-bolt', owner=1)
        self.g.mana('RRR', owner=1)
        land_w_mana_ability = self.g.battlefield('hammerheim', owner=1)
        land_w_no_mana_ability = self.g.battlefield('maze-of-ith', owner=1)

        bolt_pipeline = AbilityPipeline(1, self.gs, bolt, bolt.abilities[0], targets=[0])
        bolt_pipeline.advance()
        bolt_stack_action = next(a for a in self.gs.action_stack.actions)
        card_pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[bolt_stack_action])
        x_action = SelectXAction2(0, self.gs, card_pipeline, 2)
        x_action.play()
        card_pipeline.advance()
        card_pipeline.resolve_ability()
        bolt_countered_tap_all_mana_lands = self.gs.pending_choice.get_actions()[1]
        self.gs.choice_mgr.choose(bolt_countered_tap_all_mana_lands)
        self.assertEqual(20, self.gs.life[0])
        self.assertTrue(land_w_mana_ability.is_tapped)
        self.assertFalse(land_w_no_mana_ability.is_tapped)

    def test_power_surge(self):
        """At each player's upkeep, PS deals X damage to that player;
        X = untapped land count they controlled at the beginning of this turn."""

    def test_powerleech(self):
        """Whenever an opp's artifact becomes tapped or an opponent activates an artifact's ability without {T}
        in its activation cost, you gain 1 life."""
        self.g.battlefield('powerleech')
        tapping_artifact = self.g.battlefield('sol-ring', owner=1)
        no_tap_artifact = self.g.battlefield('book-of-rass', owner=1)
        aa = no_tap_artifact.activated_abilities[0]
        not_an_artifact = self.g.battlefield('llanowar-elves', owner=1)
        self.g.mana('GGGGGGG', owner=1)
        self.g.next_turn()

        tapping_artifact.tap()
        self.assertEqual(21, self.gs.life[0])

        self.g.activate_ability(aa, owner=1)
        self.assertEqual(22, self.gs.life[0])

        not_an_artifact.tap()
        self.assertEqual(22, self.gs.life[0])

    def test_pradesh_gypsies(self):
        """{1G}, {T}: Target creature gets -2/-0 until end of turn."""

    def test_preacher(self):
        """You may choose not to untap this creature during your untap step.
        {T}: For as long as P remains tapped, gain control of target creature of an opponent's choice they control."""

    def test_presence_of_the_master(self):
        """Whenever a player casts an enchantment spell, counter it"""
        self.g.battlefield('presence-of-the-master')
        enchantment = self.g.hand('crusade', owner=1)
        self.g.mana('WW')
        ap = AbilityPipeline(1, self.gs, enchantment, enchantment.abilities[0])
        ap.advance()
        self.assertIn(enchantment, self.g.gy[1])

    def test_priest_of_yawgmoth(self):
        """{T}, Sacrifice an artifact: Add an amount of {B} equal to the sacrificed artifact's mana value."""

    def test_primal_clay(self):
        """As PC ETB, it becomes your choice of a 3/3 artifact creature, a 2/2 artifact creature with flying,
        or a 1/6 Wall artifact creature with defender in addition to its other types."""

    def test_primordial_ooze(self):
        """At your upkeep, put a +1/+1 counter on PO.
        Then you may pay {X}, X = +1/+1 counters on it. If you don't, tap this creature & it deals X damage to you."""
        card = self.g.battlefield('primordial-ooze')
        swamp = self.g.battlefield('swamp')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, card.counters.get_count(PLUS_ONE))

        pay_mana_action = self.gs.pending_choice.get_actions()[0]
        self.gs.choice_mgr.choose(pay_mana_action)
        self.assertTrue(swamp.is_tapped)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertTrue(card.is_tapped)
        self.assertEqual(18, self.gs.life[0])
        self.assertFalse(self.gs.pending_choice)

    def test_princess_lucrezia(self):
        """{T}: Add {U}."""

    def test_prodigal_sorcerer(self):
        """{T}: This creature deals 1 damage to any target."""

    def test_psionic_blast(self):
        """Deal 4 damage to any target & 2 to yourself"""
        card = self.g.hand('psionic-blast')
        self.g.mana('UUUU')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0], targets=[1])
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertEqual([18, 16], self.gs.life)

    def test_psionic_entity(self):
        """{T}: This creature deals 2 damage to any target and 3 damage to itself."""

    def test_psychic_allergy(self):
        """As PA ETB, choose a color. At opp's upkeep, PA deals X damage to opp;
        X = nontoken perm count of the chosen color they control. At your upkeep, sac two Islands or destroy PA."""

    def test_psychic_purge(self):
        """... When a spell or ability an opp controls causes you to discard this card, that player loses 5 life."""
        # TODO: this card needs to be registered upon entry to hand and de-registered upon exit from hand
        # card = self.g.hand('psychic-purge')
        # spell_card = self.g.hand('wheel-of-fortune', owner=1)
        # self.g.mana('RRRRRR', owner=1)
        # pipeline = self.g.begin_cast(spell_card)
        # AcceptAction(0, self.gs).play()
        # self.assertEqual(15, self.gs.life[1])
        raise ValueError()

    def test_psychic_venom(self):
        """Enchant land Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller."""

    def test_puppet_master(self):
        """When host dies, bounce host instead. You may pay {UUU} to bounce this aura."""
        card = self.g.hand('puppet-master')
        host = self.g.battlefield('grizzly-bears')
        self.g.cast_and_accept(card, host, card.abilities[0])
        self.gs.pile_mgr.destroy(host)
        bounce_aura = self.gs.pending_choice.get_actions()[0]
        bounce_aura.play()
        self.assertIn(host, self.gs.hands[0])
        self.assertIn(card, self.gs.hands[0])

    def test_purelace(self):
        """Target spell or permanent becomes white. (Mana symbols on that permanent remain unchanged.)"""

    def test_pyramids(self):
        """{2}: Choose one - * Destroy target Aura attached to a land.
        * The next time target land would be destroyed this turn, remove all damage marked on it instead."""

    def test_pyrotechnics(self):
        """Pyrotechnics deals 4 damage divided as you choose among any number of targets."""


if __name__ == '__main__':
    unittest.main()
