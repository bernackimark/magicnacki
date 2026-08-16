import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import SelectXAction2
from models.actions.cast import CastWithNoSpellEffect
from models.actions.advance_phase import PassTheTurn
from models.constants import KW
from models.cost import ExileCreatureFromYourGraveyardCost
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
        first_blue_untap = self.gs.pending_choice.get_actions()[0]
        first_blue_untap.play()
        self.assertFalse(blue1.is_tapped)

        print('---------')
        print(self.gs.pending_choice.get_actions())
        print('------')
        dont_untap_anymore = self.gs.pending_choice.get_actions()[1]
        dont_untap_anymore.play()
        self.assertTrue(blue2.is_tapped)
        self.assertFalse(self.gs.pending_choice)

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
        pay_to_untap = self.gs.pending_choice.get_actions()[0]
        pay_to_untap.play()
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

    def test_martyrs_of_korlis(self):
        """As long as MOK is untapped, all damage that would be dealt to you by artifacts is dealt to MOK instead"""
        card = self.g.battlefield('martyrs-of-korlis')  # 1/6
        juggernaut = self.g.battlefield('juggernaut', owner=1)  # 5/3
        PassTheTurn(0, self.gs).play()
        self.g.combat(juggernaut, None)
        self.assertEqual(5, card.damage_received_this_turn)
        self.assertEqual(20, self.gs.life[0], 'Damage should be redirected to Martyrs Of Korlis')

        self.g.next_turn()
        card.damage_received_this_turn = 0
        card.tap()
        self.g.combat(juggernaut, None)
        self.assertEqual(0, card.damage_received_this_turn)
        self.assertEqual(15, self.gs.life[0], 'Damage should not have been redirected to MOK')

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

    def test_mirror_universe(self):
        """{T}, Sacrifice this artifact: Exchange life totals with target opponent. Activate only during your upkeep."""
        card = self.g.battlefield('mirror-universe')
        aa = card.activated_abilities[0]
        self.gs.apply_damage(card, 1, 1)  # life = [20, 19]
        self.g.activate_ability(aa)
        self.assertIn(card, self.g.gy[0])
        self.assertEqual([19, 20], self.gs.life)

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

    def test_necropolis(self):
        """Exile a creature card from your graveyard: Put X +0/+1 counters on this creature, X = the exiled card's MV"""
        self.g.graveyard('merfolk-of-the-pearl-trident')  # U
        air_elemental = self.g.graveyard('air-elemental')  # 3UU
        card = self.g.battlefield('necropolis')  # 0/1
        aa = card.activated_abilities[0]

        pipeline = AbilityPipeline(0, self.gs, card, aa.eff_spec, targets=[card])
        exile_air_elemental = ExileCreatureFromYourGraveyardCost(selected_card=air_elemental)
        pipeline.cost_result = exile_air_elemental.pay(self.gs, card)
        pipeline.advance()
        pipeline.resolve_ability()

        self.assertEqual(card.toughness, 6)
        self.assertIn(air_elemental, self.gs.exiles[0])

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
        target = self.g.battlefield('air-elemental', owner=1)  # 4/4
        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)

        self.g.next_turn()
        card.untap()
        self.assertEqual(1, target.owner_id)

        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)
        pump = self.g.hand('giant-growth')
        pump.abilities[0].effect.resolve(self.gs, pump, card)

        print('---------')
        print(card.power, target.power)  # this correctly indicates that OMOTS's power is 5
        self.gs.event_mgr.emit(StateBasedEvent())
        print(card.power, target.power)  # this correctly indicates that OMOTS's power is 5
        self.assertEqual(1, target.owner_id, 'Target should have been returned to original owner when OMOTOS pumped')
        self.assertIn(target, self.gs.boards[1])

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
        self.g.mana('U')
        self.assertFalse(any(a for a in self.gs.available_actions_from_hand()
                             if isinstance(a, AbilityPipeline) and a.source is card))

        self.g.mana('UU')
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.advance()
        possible_actions = self.gs.pending_choice.get_actions()
        self.assertEqual(1, len(possible_actions))  # 'UUU' -> X=1 only
        self.gs.choice_mgr.clear_current()

        self.g.next_turn()
        pipeline = AbilityPipeline(0, self.gs, card, card.abilities[0])
        pipeline.targets.append(c_1)
        pipeline.advance()
        pipeline.resolve_ability()
        self.assertIn(KW.ISLANDWALK, c_1.keyword_abilities)

    def test_pendelhaven(self):
        """{T}: Add {G}. {T}: Target 1/1 creature gets +1/+2 until end of turn."""
        card = self.g.battlefield('pendelhaven')
        aa = card.activated_abilities[1]
        illegal_target = self.g.battlefield('giant-spider')  # 2/4
        self.assertNotIn(illegal_target, aa.eff_spec.target_spec.get_targets(self.gs, card))

        legal_target = self.g.battlefield('merfolk-of-the-pearl-trident')  # 1/1
        self.g.activate_ability(aa, legal_target)
        self.assertEqual((2, 3), (legal_target.power, legal_target.toughness))

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

    def test_power_leak(self):
        """At host's upkeep, PL deals 2 damage to host owner. Host may pay X mana to prevent X of that damage."""
        card = self.g.battlefield('power-leak')
        host = self.g.battlefield('unstable-mutation')
        self.g.mana('GG')
        self.g.attach(card, host)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(3, len([a for a in self.gs.pending_choice.get_actions()
                                 if a.description.startswith('Pay ')]))

    def test_power_sink_1_controller_pays_path(self):
        """Counter target spell unless its controller pays {X}.
        If opponent doesn't, they tap all lands with mana abilities they control and lose all unspent mana."""
        # TODO: The land tapping part ...
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
        # TODO: The land tapping part ...
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
        bolt_countered_action = self.gs.pending_choice.get_actions()[1]
        bolt_countered_action.play()
        self.assertEqual(20, self.gs.life[0])

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

    def test_presence_of_the_master(self):
        """Whenever a player casts an enchantment spell, counter it"""
        self.g.battlefield('presence-of-the-master')
        enchantment = self.g.hand('crusade', owner=1)
        self.g.mana('WW')
        ap = AbilityPipeline(1, self.gs, enchantment, enchantment.abilities[0])
        ap.advance()
        self.assertIn(enchantment, self.g.gy[1])

    def test_primordial_ooze(self):
        """At your upkeep, put a +1/+1 counter on PO.
        Then you may pay {X}, X = +1/+1 counters on it. If you don't, tap this creature & it deals X damage to you."""
        card = self.g.battlefield('primordial-ooze')
        swamp = self.g.battlefield('swamp')
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertEqual(1, card.counters.get_count(PLUS_ONE))

        pay_mana_action = self.gs.pending_choice.get_actions()[0]
        pay_mana_action.play()
        self.assertTrue(swamp.is_tapped)

        self.g.next_turn()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP)
        self.assertTrue(card.is_tapped)
        self.assertEqual(18, self.gs.life[0])
        self.assertFalse(self.gs.pending_choice)

    # def test_psychic_purge(self):
    #     """... When a spell or ability an opp controls causes you to discard this card, that player loses 5 life."""
    #     # TODO: this card needs to be registered upon entry to hand and de-registered upon exit from hand
    #     card = self.g.hand('psychic-purge')
    #     spell_card = self.g.hand('wheel-of-fortune', owner=1)
    #     self.g.mana('RRRRRR', owner=1)
    #     pipeline = self.g.begin_cast(spell_card)
    #     AcceptAction(0, self.gs).play()
    #     self.assertEqual(15, self.gs.life[1])

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


if __name__ == '__main__':
    unittest.main()
