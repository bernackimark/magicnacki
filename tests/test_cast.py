import unittest

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastPermanentAction
from tests.setup_helpers import TestGame


class TestCast(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs

    def test_cast_permanent_w_no_effects(self):
        card = self.g.hand('merfolk-of-the-pearl-trident')
        self.g.mana('U')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        cast_action = next(a for a in available_actions if isinstance(a, CastPermanentAction) and a.source is card)
        cast_action.play()
        self.assertIn(card, self.gs.boards[0])

    def test_cast_card_with_effects_but_no_spell(self):
        card = self.g.hand('ankh-of-mishra')
        self.g.mana('RRRRRR')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        cast_action = next(a for a in available_actions if isinstance(a, CastPermanentAction) and a.source is card)
        cast_action.play()
        self.assertTrue(any(e.source is card for _, effects in self.gs.event_mgr._event_listeners.items()
                            for e in effects))

    def test_cast_card_with_spell_with_no_effect(self):
        card = self.g.hand('animate-wall')
        host = self.g.battlefield('wall-of-brambles')
        self.g.mana('W')
        available_actions = [a for a in self.gs.available_actions_from_hand()]
        ability_action = next(a for a in available_actions if isinstance(a, AbilityPipeline) and a.source is card)
        ability_action.targets.append(host)
        ability_action.resolve_ability()
        self.assertTrue(card.host is host)


if __name__ == '__main__':
    unittest.main()
