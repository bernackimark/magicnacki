import unittest

from models.actions.cast import CastToTargetAddToStack
from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.special import Attach, PayManaAndOrTakeDamage
from models.actions.stack_accept_counter import AcceptAction
from models.actions.tap_untap import Untap, PayManaToUntapAction
from models.events_all import StateBasedEvent
from models.phase_manager import Phase
from tests.setup_helpers import TestGame

class TestCardsMNOP(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_martyrs_of_korlis(self):
        """As long as MOK is untapped, all damage that would be dealt to you by artifacts is dealt to MOK instead"""
        card = self.g.battlefield('martyrs-of-korlis')  # 1/6
        juggernaut = self.g.battlefield('juggernaut', owner=1)  # 5/3
        PassTheTurn(0, self.gs).play()
        self.g.combat(juggernaut, None)
        self.assertEqual(5, card.damage_received_this_turn)
        self.assertEqual(20, self.gs.score_mgr.life[0], 'Damage should be redirected to Martyrs Of Korlis')

        self.g.next_turn()
        card.damage_received_this_turn = 0
        card.tap()
        self.g.combat(juggernaut, None)
        self.assertEqual(0, card.damage_received_this_turn)
        self.assertEqual(15, self.gs.score_mgr.life[0], 'Damage should not have been redirected to MOK')

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
        self.assertTrue(any(isinstance(a, Untap) for a in self.gs.pending_choice.get_actions()))

        card.untap()
        self.assertEqual(1, target.owner_id)

        self.g.activate_ability(aa, target)
        self.assertEqual(0, target.owner_id)
        pump = self.g.hand('giant-growth')
        pump.abilities[0].effect.resolve(self.gs, pump, card)  # type: ignore
        # TODO: debug print statements are firing here from inside of OldManOfTheSeaPowerCheck, showing its power as 2

        # print(card.power, target.power)  # this correctly indicates that OMOTS's power is 5
        # self.gs.event_mgr.emit(StateBasedEvent, self.gs)
        # print(card.power, target.power)  # this correctly indicates that OMOTS's power is 5
        # self.assertEqual(1, target.owner_id, 'Target should have been returned to original owner when OMOTOS pumped')

    def test_orcish_artillery(self):
        """{T}: This creature deals 2 damage to any target and 3 damage to you"""
        card = self.g.battlefield('orcish-artillery')
        aa = card.activated_abilities[0]
        target = self.g.battlefield('grizzly-bears', owner=1)  # 2/2

        self.g.next_turn()
        self.g.activate_ability(aa, target)
        self.assertIn(target, self.gs.pile_mgr.graveyards[1])

        self.g.next_turn()
        self.g.activate_ability(aa, 1)
        self.assertEqual([14, 18], self.gs.score_mgr.life)

    def test_paralyze(self):
        """When this Aura enters, tap host. Host doesn't untap during its untap step.
        At host's upkeep, that player may pay {4} to untap host."""
        card = self.g.battlefield('paralyze')
        host = self.g.battlefield('grizzly-bears', owner=1)
        self.g.mana('B')
        Attach(0, self.gs, card, host).play()
        card.abilities[2].effect.resolve(self.gs, card, host)  # type: ignore
        self.assertTrue(host.is_tapped)

        self.g.mana('GGGG', owner=1)
        PassTheTurn(0, self.gs).play()
        self.assertTrue(host.is_tapped)
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.assertTrue(any(isinstance(a, PayManaToUntapAction) for a in self.gs.pending_choice.get_actions()))

    def test_power_leak(self):
        """At host's upkeep, PL deals 2 damage to host owner. Host may pay X mana to prevent X of that damage."""
        card = self.g.battlefield('power-leak')
        host = self.g.battlefield('unstable-mutation')
        self.g.mana('GG')
        Attach(0, self.gs, card, host).play()
        self.gs.phase_mgr.set_phase(Phase.UPKEEP, self.gs)
        self.assertEqual(3, len([a for a in self.gs.pending_choice.get_actions()
                                 if isinstance(a, PayManaAndOrTakeDamage)]))

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
        self.assertEqual(21, self.gs.score_mgr.life[0])

        self.g.activate_ability(aa, owner=1)
        self.assertEqual(22, self.gs.score_mgr.life[0])

        not_an_artifact.tap()
        self.assertEqual(22, self.gs.score_mgr.life[0])

    # def test_psychic_purge(self):
    #     """... When a spell or ability an opp controls causes you to discard this card, that player loses 5 life."""
    #     # TODO: this card needs to be registered upon entry to hand and de-registered upon exit from hand
    #     card = self.g.hand('psychic-purge')
    #     spell_card = self.g.hand('wheel-of-fortune', owner=1)
    #     self.g.mana('RRRRRR', owner=1)
    #     CastToTargetAddToStack(1, self.gs, spell_card, None, spell_card.abilities[0]).play()
    #     AcceptAction(0, self.gs).play()
    #     self.assertEqual(15, self.gs.score_mgr.life[1])


if __name__ == '__main__':
    unittest.main()
