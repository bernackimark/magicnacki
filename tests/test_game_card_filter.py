import unittest

from tests.setup_helpers import TestGame


class TestCardFilter(unittest.TestCase):
    def setUp(self):
        self.g = TestGame()
        self.gs = self.g.gs
        for h in self.gs.pile_mgr.hands:
            h.cards.clear()

    def test_in_play(self):
        lion = self.g.battlefield("savannah-lions")
        self.g.hand("lightning-bolt")
        cards = self.gs.card_filter.in_play().result()
        self.assertIn(lion, cards)
        self.assertEqual(1, len(cards))

    def test_in_player_hand(self):
        bolt = self.g.hand("lightning-bolt")
        self.g.hand("counterspell", owner=1)
        cards = self.gs.card_filter.in_player_hand(0).result()
        self.assertEqual([bolt], cards)

    def test_in_player_graveyard(self):
        bear = self.g.graveyard("grizzly-bears", 1)
        cards = self.gs.card_filter.in_player_graveyard(1).result()
        self.assertEqual([bear], cards)

    def test_by_slug(self):
        bear1 = self.g.battlefield("grizzly-bears")
        bear2 = self.g.battlefield("grizzly-bears")
        self.g.battlefield("savannah-lions")
        cards = self.gs.card_filter.in_play().by_slug("grizzly-bears").result()
        self.assertCountEqual([bear1, bear2], cards)

    def test_creatures(self):
        lion = self.g.battlefield("savannah-lions")
        self.g.battlefield("black-lotus")
        cards = self.gs.card_filter.in_play().creatures().result()
        self.assertEqual([lion], cards)

    def test_artifacts(self):
        lotus = self.g.battlefield("black-lotus")
        self.g.battlefield("savannah-lions")
        ornithopter = self.g.battlefield('ornithopter')
        cards = self.gs.card_filter.in_play().artifacts().result()
        self.assertEqual([lotus, ornithopter], cards)

    def test_lands(self):
        plains = self.g.battlefield("plains")
        self.g.battlefield("savannah-lions")
        cards = self.gs.card_filter.in_play().lands().result()
        self.assertEqual([plains], cards)

    def test_by_color(self):
        white = self.g.battlefield("savannah-lions")
        self.g.battlefield("monss-goblin-raiders")
        cards = self.gs.card_filter.in_play().by_color("W").result()
        self.assertEqual([white], cards)

    def test_tapped(self):
        lion = self.g.battlefield("savannah-lions")
        lion.tap()
        cards = self.gs.card_filter.in_play().tapped().result()
        self.assertEqual([lion], cards)

    def test_has_keyword(self):
        knight = self.g.battlefield("black-knight")
        cards = self.gs.card_filter.in_play().has("First Strike").result()
        self.assertEqual([knight], cards)

    def test_chain_filters_order_1(self):
        self.g.battlefield("savannah-lions")
        self.g.battlefield("white-knight")
        self.g.hand("white-knight")
        cards = self.gs.card_filter.in_play().creatures().white().result()
        self.assertEqual(2, len(cards))

    def test_chain_filters_order_2(self):
        self.g.battlefield("savannah-lions")
        self.g.battlefield("white-knight")
        self.g.hand("white-knight")
        cards = self.gs.card_filter.white().creatures().in_play().result()
        self.assertEqual(2, len(cards))

    def test_result_resets_filter(self):
        self.g.battlefield('savannah-lions')
        self.g.hand('lightning-bolt')
        self.g.hand('monss-goblin-raiders')
        self.g.hand('white-knight')
        result = self.gs.card_filter.in_play().creatures().result()
        self.assertEqual(1, len(result))

        result = self.gs.card_filter.in_player_hand(0).red().result()
        self.assertEqual(2, len(result))


if __name__ == '__main__':
    unittest.main()
