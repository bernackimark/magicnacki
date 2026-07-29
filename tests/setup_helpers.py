from __future__ import annotations
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import Any

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastPermanentAction
from models.actions.end_step_pass_turn import PassTheTurn
from models.effects.base import ActivatedAbility, EffSpec
from models.systems.phase import Phase
from data.user_data import get_user
from engine import Engine, deflate_costs
from models.constants import Mulligan
from models.game_card.card import CardUniverse
from models.game_card.game_card import GameCard
from models.deck import Deck
from models.systems.match import MatchManager
from models.zone import Zone
from players import ConsolePlayer
from renderers import ConsoleRenderer


load_dotenv()
GAME_TESTING_SETTINGS_PATH = Path(os.getenv('GAME_TESTING_SETTINGS'))


class TestGame:
    """A wrapper around Engine/GameState that provides helpful methods for setting up board states;
    its methods are shortcuts and do not emit to the event system, so they should be used specifically in setup"""
    def __init__(self, file_path_str: str = GAME_TESTING_SETTINGS_PATH,
                 settings_key: str = 'engine_testing_setup_a', test_mode: bool = True):
        engine, cu = self._create_engine_and_universe(file_path_str, settings_key, test_mode)
        self.engine = engine
        self.cu = cu
        self.gs = self.engine.match_manager.create_game_state()
        self.engine.gs = self.gs

    def card(self, slug: str, player_id: int = 0) -> GameCard:
        game_card = GameCard(self.cu[slug], player_id)
        game_card.game_state = self.gs
        self.gs.pile_mgr.libraries[player_id].append(game_card)
        return game_card

    def battlefield(self, *slugs, cnt=1, owner=0, pay_mana=False) -> GameCard | list[GameCard]:
        """Warning: if the card has a spell action, please also use resolve_spell();
        From any amount of positional argument slugs, creates GameCard(s);
        Imitates CastPermanentAction, except paying mana is optional & no emissions
        Returns GameCard or list[GameCard]"""
        cards = []
        for slug in slugs:
            for _ in range(cnt):
                card = self.card(slug, owner)
                self.gs.pile_mgr.move_card(card, Zone.BATTLEFIELD, cause='cast', emit_zone_event=False)
                if pay_mana:
                    self.gs.mana_pools[owner].pay(card.casting_cost)
                if card.is_land:
                    self.gs.turn_mgr.has_played_land = True
                from models.effects.base import Listener
                for eff_spec in card.abilities:
                    if not eff_spec.is_aa and isinstance(eff_spec.effect, Listener):
                        self.gs.event_mgr.register(eff_spec.effect, card)
                        print(f"Registered listener for {card.props.name}: {eff_spec.effect}")
                if len(slugs) == 1 and cnt == 1:
                    return card
                cards.append(card)
        return cards

    def hand(self, slug, owner=0) -> GameCard:
        """Create GameCard, update Zone to Battlefield without emitting"""
        card = self.card(slug, owner)
        self.gs.pile_mgr.move_card(card, Zone.HAND, emit_zone_event=False)
        return card

    def graveyard(self, slug, owner=0) -> GameCard:
        """Create GameCard, update Zone to Graveyard without emitting"""
        card = self.card(slug, owner)
        self.gs.pile_mgr.move_card(card, Zone.GRAVEYARD, emit_zone_event=False)
        return card

    def library(self, slug, owner=0) -> GameCard:
        """Create GameCard, move to top of library, update Zone to Library without emitting"""
        card = self.card(slug, owner)
        card_in_lib = self.gs.pile_mgr.libraries[0].pop()
        self.gs.pile_mgr.libraries[0].insert(0, card_in_lib)
        # self.gs.pile_mgr.move_card(card, Zone.LIBRARY, emit_zone_event=False)
        return card

    def mana(self, mana: str, owner=0) -> None:
        """A shorthand way of getting lands/available mana onto the battlefield; 'RRU' adds two mountains & an island"""
        lookup = {'B': 'swamp', 'G': 'forest', 'R': 'mountain', 'U': 'island', 'W': 'plains'}
        for color in mana:
            self.battlefield(lookup[color], owner=owner)

    def activate_ability(self, aa: ActivatedAbility, target: GameCard | int | None = None, owner: int = 0):
        pipeline = AbilityPipeline(owner, self.gs, aa.source, aa.eff_spec)
        if target is not None:
            pipeline.targets.append(target)
        for extra_cost in aa.eff_spec.extra_costs:
            pipeline.selected_extra_costs.append(extra_cost)
        pipeline.advance()
        pipeline.resolve_ability()

    def begin_cast(self, card: GameCard, spell: EffSpec = None) -> AbilityPipeline:
        if not spell:
            spell = card.abilities[0]
        pipeline = AbilityPipeline(card.owner_id, self.gs, card, spell)
        pipeline.advance()
        return pipeline

    def cast_and_accept(self, card: GameCard, target: GameCard | int | None = None,
                        eff_spec: EffSpec | None = None, owner: int = 0, add_lots_of_mana: bool = True):
        if card.is_land:
            CastPermanentAction(owner, self.gs, card).play()
            return
        # add a boatload of mana
        if add_lots_of_mana and card.casting_cost:
            casting_colors = {color for color in card.casting_cost if color in {'B', 'G', 'R', 'U', 'W'}}
            if casting_colors:
                for color in casting_colors:
                    self.mana(color * 6, owner=owner)
            else:
                self.mana('U' * 6, owner=owner)

        pipeline = AbilityPipeline(owner, self.gs, card, eff_spec)
        if target is not None:
            pipeline.targets.append(target)
        pipeline.advance()
        pipeline.resolve_ability()

    def card_has_a_registered_listener(self, card: GameCard) -> bool:
        return any(e.source is card for entries in self.gs.event_mgr.event_listeners.values() for e in entries)

    def clear_hands(self) -> None:
        [h.clear() for h in self.gs.hands]

    def combat(self, attacker: GameCard, blockers: GameCard | list[GameCard] | None):
        self.gs.combat_mgr.create_combat(attacker)
        if blockers is None:
            pass
        elif isinstance(blockers, GameCard):
            self.gs.combat_mgr.add_blocker(attacker, blockers)
        else:
            for blocker in blockers:
                self.gs.combat_mgr.add_blocker(attacker, blocker)
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS)
        self.gs.phase_mgr.set_phase(Phase.PRE_COMBAT_DAMAGE)
        if self.gs.combat_mgr.has_first_strike_step:
            self.gs.phase_mgr.set_phase(Phase.FIRST_STRIKE_DAMAGE)
        self.gs.phase_mgr.set_phase(Phase.COMBAT_DAMAGE)

    def next_turn(self, go_to_opp_turn: bool = False):
        """Passes the current turn; passes the next turn; returning action back to the original player"""
        self.gs.phase_mgr.set_phase(Phase.END_TURN_EFFECTS)
        PassTheTurn(self.gs.player_turn_idx, self.gs).play()
        if go_to_opp_turn:
            return
        self.gs.phase_mgr.set_phase(Phase.END_TURN_EFFECTS)
        PassTheTurn(self.gs.player_turn_idx, self.gs).play()

    def resolve_spell(self, card: GameCard, target: Any = None, spell: EffSpec | None = None):
        """Executes eff_spec.effect.resolve();
        if the caller is lazy & provides no spell, they are assumed to want the card's first spell ability"""
        if not spell:
            spell = next(_ for _ in card.spells)
        spell.effect.resolve(self.gs, card, target)

    @property
    def gy(self) -> list[list[GameCard | None]]:
        return self.gs.pile_mgr.graveyards

    @staticmethod
    def _create_engine_and_universe(file_path_str, settings_key, test_mode) -> tuple[Engine, CardUniverse]:
        """From provided path string & key, pull JSON; create CardUniverse; create decks;
        deflate casting costs, if applicable; set rules; create & return a fresh Engine oboject"""
        import json
        with open(file_path_str, 'r') as f:
            data = json.load(f)
            data = data[settings_key]

        universe = CardUniverse(data['universe'])

        decks = [Deck.from_json(deck_id, str(i)) for i, deck_id in enumerate((data['deck_0'], data['deck_1']))]

        # create players
        players = []
        for i, user_id in enumerate(data['users']):
            user_data = get_user(user_id)
            player = ConsolePlayer(i, user_data.handle, user_data.is_bot)
            players.append(player)

        # would put in the testing JSON, but not sure how to convert mulligan to enum member
        rules = {'mulligan': Mulligan.LONDON_WITH_GENTLEMENS, 'best_of': 3}

        eng = Engine(players=players, renderer=ConsoleRenderer(),
                     match_manager=MatchManager(len(players), rules, decks, universe.token_cards,
                                                first_to_act=data['starting_deck']))
        if test_mode:
            deflate_costs(eng.match_manager.deck_game_cards)
        return eng, universe
