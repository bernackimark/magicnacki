import unittest

from models.actions.end_step_pass_turn import PassTheTurn
from models.actions.tap_untap import Untap
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


if __name__ == '__main__':
    unittest.main()
