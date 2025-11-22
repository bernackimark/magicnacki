import abc
from abc import ABC
from dataclasses import dataclass, field
import random

from card_filter import CardFilter
from build_deck import Deck
from models.activated_ability import ActivatedAbility
from models.game_card import GameCard, TAP_REGISTRY, UNTAP_REGISTRY, SUCCESSFUL_CAST
from models.board import Board, casting_weight
from models.combat import Combat
from models.hand import Hand
from models.turn import Turn
from phase_fsm import Phase
from utils import flip


@dataclass
class Action(ABC):
    player_idx: int
    gs: "GameState"

    @abc.abstractmethod
    def play(self) -> None:
        ...

@dataclass
class ActionStack:
    _actions: list[Action] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._actions)

    @property
    def first_actor_idx(self) -> int:
        return self._actions[0].player_idx

    @property
    def last_actor_idx(self) -> int:
        return self._actions[-1].player_idx

    @property
    def action_on_idx(self) -> int:
        return flip(self.last_actor_idx)

    @property
    def last_action(self) -> Action:
        return self._actions[-1]

    def add(self, action: Action, gs: "GameState") -> None:
        self._actions.append(action)
        gs.action_on_idx = flip(gs.action_on_idx)

    def clear(self) -> None:
        self._actions.clear()

@dataclass
class DrawCard(Action):
    def __repr__(self) -> str:
        return 'Draw a Card'

    def play(self) -> None:
        hand = self.gs.hands[self.player_idx]
        deck = self.gs.decks[self.player_idx]
        hand.cards.append(deck.cards.pop())
        hand.sort_cards()
        self.gs.phase = Phase.CAST

@dataclass
class CastToBoard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Cast {self.card.props.name}"

    def play(self) -> None:
        board = self.gs.boards[self.player_idx]
        board.pay_casting_weight(self.card.props.casting_weight, self.gs)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        board.play_to_board(self.card)
        if self.card.props.is_land:
            self.gs.turn.has_played_land = True

        # TODO: for the sake of testing, perms are being auto-cast, instead of being added to the stack
        if func := SUCCESSFUL_CAST.get(self.card.props.slug):
            print(f"Successfully cast {self.card.props.name}")
            func(self.gs, self.card, None)

@dataclass
class CastToTargetAddToStack(Action):
    card: GameCard
    target: GameCard | list[GameCard] | None

    def __repr__(self) -> str:
        target_text = ''
        if isinstance(self.target, list) and self.target:
            target_text = f", targeting {', '.join([c.props.name for c in self.target])}"
        elif isinstance(self.target, GameCard):
            target_text = ', targeting' + self.target.props.name
        return f"Cast {self.card.props.name}{target_text}"

    def play(self) -> None:
        board = self.gs.boards[self.player_idx]
        board.pay_casting_weight(self.card.props.casting_weight, self.gs)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.add(self, self.gs)

@dataclass
class CastCounter(Action):
    card: GameCard
    target: Action

    def __repr__(self):
        return f"Cast {self.card.props.name} to counter {self.target}"

    def play(self) -> None:
        board = self.gs.boards[self.player_idx]
        board.pay_casting_weight(self.card.props.casting_weight, self.gs)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.add(self, self.gs)

@dataclass
class CreatureAttack(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Add {self.card.__repr__()} to attack"

    def play(self) -> None:
        self.card.tap(self.gs)
        self.gs.combats.append(Combat(self.gs, self.card))

@dataclass
class BeginCombat(Action):

    def __repr__(self) -> str:
        return "Begin Combat"

    def play(self) -> None:
        self.gs.phase = Phase.DECLARE_ATTACKERS

@dataclass
class FinishDeclaringAttackers(Action):

    def __repr__(self) -> str:
        return "Done Declaring Attackers"

    def play(self) -> None:
        self.gs.phase = Phase.DECLARE_BLOCKERS
        self.gs.action_on_idx = flip(self.gs.action_on_idx)

@dataclass
class AssignBlocker(Action):
    blocker: GameCard
    attacker: GameCard

    def __repr__(self) -> str:
        return f"Block {self.attacker} with {self.blocker}"

    def play(self) -> None:
        for com in self.gs.combats:
            if com.attacker == self.attacker:
                com.blockers.append(self.blocker)

@dataclass
class FinishBlocking(Action):

    def __repr__(self) -> str:
        return f"Finish Blocks"

    def play(self) -> None:
        self.gs.phase = Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES

@dataclass
class MoveToEndStep(Action):

    def __repr__(self) -> str:
        return "Move to End Step"

    def play(self) -> None:
        self.gs.phase = Phase.END_STEP

@dataclass
class DiscardCard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Discard {self.card} to graveyard"

    def play(self) -> None:
        self.gs.send_to_graveyard(self.card)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)

@dataclass
class PassTheTurn(Action):

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.player_turn_idx = flip(self.gs.player_turn_idx)
        self.gs.action_on_idx = self.gs.player_turn_idx
        self.gs.turn = Turn(self.gs.player_turn_idx, flip(self.gs.player_turn_idx))
        self.gs.turn_number += 1
        self.gs.phase = Phase.UNTAP

@dataclass
class ActivateAbility(Action):
    ability: ActivatedAbility
    target: GameCard | None = None

    def __repr__(self) -> str:
        return f"Activating Ability: {self.ability.card.props.name}"

    def play(self) -> None:
        # Pay tap cost
        if self.ability.cost_tap:
            self.ability.card.tap(self.gs)

        # Pay mana cost
        if self.ability.cost_mana:
            self.gs.boards[self.ability.card.orig_owner_id].pay_casting_weight(casting_weight(self.ability.cost_mana), self.gs)

        # Execute effect
        self.ability.effect(self.gs, self.ability.card, self.target)

@dataclass
class AcceptAction(Action):
    def __repr__(self) -> str:
        return f"Accept {self.gs.action_stack.last_action}"

    def play(self) -> None:
        last_action: CastToTargetAddToStack = self.gs.action_stack.last_action
        card = last_action.card
        target = last_action.target
        if card.props.is_aura:
            card.attached_to = target
            target.auras.append(card)
            self.gs.boards[target.orig_owner_id].play_to_board(card)

        if func := SUCCESSFUL_CAST.get(card.props.slug):
            print(f"Successfully cast {card.props.name}")
            func(self.gs, card, target)

        self.gs.action_on_idx = self.gs.action_stack.first_actor_idx  # action returns to the first actor
        self.gs.action_stack.clear()


@dataclass
class CounterAction(Action):
    action: Action

    def __repr__(self) -> str:
        return f"In response to {self.gs.action_stack.last_action}: {self.action}"

    def play(self) -> None:
        self.gs.action_stack.add(self.action, self.gs)
        self.gs.action_on_idx = flip(self.gs.action_on_idx)


class GameState:
    def __init__(self, player_cnt: int, player_turn_idx: int, decks: list[Deck]):
        self.player_cnt = player_cnt
        self.player_turn_idx = player_turn_idx
        self.decks = decks
        self.decks_all_cards = self.decks.copy()
        self.life = [20, 20]
        self.action_on_idx: int = self.player_turn_idx
        self.turn = Turn(self.player_turn_idx, flip(self.player_turn_idx))
        self.boards: list[Board] = [Board(i) for i in range(self.player_cnt)]
        self.graveyards: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.exiles: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.hands: list[Hand] = [Hand(sort_pref=Hand.SortOrient.L_TO_R) for _ in range(self.player_cnt)]
        self.phase = Phase.UNTAP
        self.action_stack = ActionStack()
        self.game_history: list[tuple[int, Action]] = []  # turn number & Action; appended to in engine.play()
        self.turn_number = 1
        self.combats: list[Combat] = []
        self.card_filter = CardFilter(self)
        self.is_game_over: bool = False

        for i in range(self.player_cnt):
            deck = self.decks[i]
            random.shuffle(deck.cards)
            hand = self.hands[i]
            self.draw(hand, deck.cards, 7)
            hand.sort_cards()

    @property
    def all_cards(self) -> list[GameCard]:
        return ([c for b in self.decks for c in b.cards] + [c for h in self.hands for c in h.cards] +
                [c for g in self.graveyards for c in g] + [c for e in self.exiles for c in e] +
                [c for b in self.boards for c in b.cards])

    @staticmethod
    def draw(hand: Hand, source_pile: list[GameCard], card_cnt: int):
        for i in range(card_cnt):
            hand.cards.append(source_pile.pop(0))
            hand.sort_cards()

    def get_card_from_boards(self, card_id: int) -> GameCard | None:
        return next((c for b in self.boards for c in b.cards if c.id == card_id), None)

    def get_card_from_board(self, board_idx: int, card_id: int) -> GameCard | None:
        return next((c for c in self.boards[board_idx].cards if c.id == card_id), None)

    def _remove_from_board(self, c: GameCard) -> GameCard | None:
        if self.get_card_from_board(c.orig_owner_id, c.id):
            self.boards[c.orig_owner_id].remove_from_board(c)
            for a in c.auras:
                self.send_to_graveyard(a)
            c.clear_all_mods()
            return c

    def send_to_graveyard(self, c: GameCard):
        if not self._remove_from_board(c):
            return
        self.graveyards[c.orig_owner_id].append(c)
        print(f'{c} has been sent to the graveyard')
        self._send_to_graveyard_or_exile(c)

    def send_to_exile(self, c: GameCard):
        if not self._remove_from_board(c):
            return
        self.exiles[c.orig_owner_id].append(c)
        print(f'{c} has been exiled')
        self._send_to_graveyard_or_exile(c)

    def _send_to_graveyard_or_exile(self, c: GameCard):
        if c.props.is_aura:
            c.attached_to = None
        for card in c.auras:
            if card.props.slug == 'creature-bond':
                self.decrement_life(c.orig_owner_id, c.props.toughness, card)
                print(f"Creature Bond reduces player #{c.orig_owner_id}'s life by {c.props.toughness}")
        if c.props.slug == 'crusade':
            for white_creature in self.card_filter.creatures().by_color('W').result():
                white_creature.remove_perm_mod_by_slug('crusade')
        c.clear_all_mods()

    def return_to_hand(self, c: GameCard):
        hand = self.hands[c.orig_owner_id]
        hand.cards.append(c)
        for a in c.auras:
            self.send_to_graveyard(a)
        c.clear_all_mods()
        hand.sort_cards()

    def increment_life(self, p_id: int, amt: int):
        print(f"Increasing player #{p_id}'s life by {amt}. Life is now at {self.life}")
        self.life[p_id] += amt

    def decrement_life(self, p_id: int, amt: int, source: GameCard):
        self.life[p_id] -= amt
        print(f"Reducing player #{p_id}'s life by {amt}. Life is now at {self.life}")
        if 'backfire' in {a.props.slug for a in source.auras}:
            self.life[flip(p_id)] -= amt
        if self.life[p_id] <= 0 < self.life[flip(p_id)]:
            print(f"Player #{p_id} has lost")
            self.is_game_over = True
        elif self.life[p_id] <= 0 and self.life[flip(p_id)] <= 0:
            print(f"Both players have lost")
            self.is_game_over = True

    def apply_tap_effects(self, c: GameCard):
        for cond, func in TAP_REGISTRY:
            if cond(self, c):
                func(self, c)

    def apply_untap_effects(self, c: GameCard):
        for cond, func in UNTAP_REGISTRY:
            if cond(self, c):
                func(self, c)

    def untap(self):
        """Untap all cards on in-turn player's board; remove summoning sickness"""
        for c in self.boards[self.player_turn_idx].cards:
            for turn_num, act in self.game_history:
                if isinstance(act, CastToBoard) and act.card.id == c.id and self.turn_number - turn_num == 2:
                    c.has_summoning_sickness = False
            if not c.is_tapped:
                continue
            c.untap(self)

    def get_activated_abilities(self, c: GameCard) -> list["ActivateAbility"]:
        actions: list[ActivateAbility] = []

        for ability in c.abilities:
            # Skip abilities that can't currently be activated
            if not ability.can_activate(self):
                continue

            # No target needed → create a single action
            if ability.target_filter is None:
                actions.append(ActivateAbility(self.action_on_idx, self, ability, None))
                continue

            # Target needed → get all legal targets
            targets = ability.target_filter(self, c)

            for t in targets:
                actions.append(ActivateAbility(self.action_on_idx, self, ability, t))

        return actions

    def get_available_actions(self, p_id: int) -> list[Action] | None:
        available_actions: list[Action] = []
        hand = self.hands[p_id]
        board = self.boards[p_id]

        # if there is something on the stack, respond & resolve, don't seek out other available actions
        if len(self.action_stack):
            available_actions.append(AcceptAction(p_id, self))

            # TODO: activated abilities should also be allowed
            allowed_cards = hand.instants + hand.sorceries if p_id == self.player_turn_idx else hand.sorceries
            playable_cards: list[GameCard] = [c for c in allowed_cards if board.can_card_meet_casting_cost(c)]

            for c in playable_cards:
                if c.props.slug in ('counterspell',):
                    target: Action = self.action_stack.last_action
                    available_actions.append(CastCounter(p_id, self, c, target))
                    continue
                target_cards: list[GameCard] = c.get_cast_targets(self)
                if not target_cards:
                    available_actions.append(CastToTargetAddToStack(p_id, self, c, None))
                    continue
                for t in target_cards:
                    available_actions.append(CastToTargetAddToStack(p_id, self, c, t))

            return available_actions

        if self.phase == Phase.PASS_THE_TURN:
            PassTheTurn(self.player_turn_idx, self).play()
            return

        if self.phase == Phase.UNTAP:
            self.untap()
            self.phase = Phase.UPKEEP
            return

        if self.phase == Phase.UPKEEP:
            for c in self.boards[self.player_turn_idx].cards:
                c.on_upkeep(self)
                for a in c.auras:
                    a.on_upkeep(self)

            self.phase = Phase.DRAW
            return

        if self.phase == Phase.DRAW:
            return [DrawCard(p_id, self)]

        if self.phase == Phase.CAST:
            available_actions.append(MoveToEndStep(p_id, self))
            # cast; compare its casting cost to the board to see if it can cast
            for i, c in enumerate(hand.cards):
                if not board.can_card_meet_casting_cost(c):
                    continue
                elif c.props.is_land and self.turn.has_played_land:
                    continue
                elif c.props.is_permanent and not c.props.is_aura:
                    available_actions.append(CastToBoard(p_id, self, c))
                else:
                    target_cards: list[GameCard] = c.get_cast_targets(self)
                    # cards that need targets but can't find any, skip ... ex. creature-bond needs a creature
                    if isinstance(target_cards, list) and not target_cards:  # target_cards = []
                        continue
                    # cards that do not require a target
                    if target_cards is None:
                        available_actions.append(CastToTargetAddToStack(p_id, self, c, None))
                        continue
                    # for all possible targets, add as an available action
                    for t in target_cards:
                        available_actions.append(CastToTargetAddToStack(p_id, self, c, t))

            # declare combat
            for c in board.cards:
                if c.can_attack and not c.has_summoning_sickness:
                    available_actions.append(BeginCombat(p_id, self))
                    break

        if self.phase == Phase.DECLARE_ATTACKERS:
            # add attackers
            for c in board.cards:
                if c not in [com.attacker for com in self.combats] and not c.has_summoning_sickness:
                    if 'Wall' in c.props.card_sub_types and 'animate-wall' in {a.props.slug for a in c.auras}:
                        c.can_attack = True
                    if c.can_attack:
                        available_actions.append(CreatureAttack(p_id, self, c))

            # finish declaring attackers; move to declare blockers
            if self.combats:
                available_actions.append(FinishDeclaringAttackers(p_id, self))

        if self.phase == Phase.DECLARE_BLOCKERS:
            remaining_blockers = [c for c in self.boards[self.action_on_idx].available_blockers
                                  if c not in [c for com in self.combats for c in com.blockers]]
            for blocker in remaining_blockers:
                for com in self.combats:
                    if 'Flying' in com.attacker.keyword_abilities and 'Flying' not in blocker.keyword_abilities and 'Reach' not in blocker.keyword_abilities:
                        continue
                    if com.attacker.props.slug == 'amrou-kithkin' and blocker.power > 3:
                        continue
                    if 'seeker' in {a.props.slug for a in com.attacker.auras}:
                        if 'Artifact' not in blocker.props.card_types or 'U' not in blocker.props.colors:
                            continue
                    available_actions.append(AssignBlocker(self.action_on_idx, self, blocker, com.attacker))
            available_actions.append((FinishBlocking(self.action_on_idx, self)))

        if self.phase == Phase.END_STEP:
            for c in self.card_filter.in_play().creatures().result():
                c.pt_temps.clear()
                c.kwa_temps.clear()
            self.phase = Phase.DISCARD
            return

        if self.phase == Phase.DISCARD:
            hand = self.hands[self.player_turn_idx]
            if len(hand.cards) > 7:
                for c in hand.cards:
                    available_actions.append(DiscardCard(self.player_turn_idx, self, c))
            else:
                self.phase = Phase.CREATURES_HEAL
                return

        if self.phase == Phase.CREATURES_HEAL:
            for deck in self.decks_all_cards:
                for c in deck.cards:
                    c.combat_damage_dealt = 0
                    c.combat_damage_received = 0
            self.phase = Phase.END_TURN_EFFECTS
            return

        if self.phase == Phase.END_TURN_EFFECTS:
            for d in self.decks_all_cards:
                for c in d.cards:
                    c.pt_temps.clear()
                    c.kwa_temps.clear()
            self.phase = Phase.PASS_THE_TURN
            return

        if self.phase == Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES:
            #  TODO: attackers & blockers have been declared
            #   this would normally allow players to cast instants, but let's skip that and instead ...
            #   we're also not yielding control after first strike, instead bundling all together
            self.phase = Phase.FIRST_STRIKE_DAMAGE
            self.phase = Phase.COMBAT_DAMAGE
            for com in self.combats:
                com.handle_damage()
            self.phase = Phase.COMBAT_END
            self.combats.clear()
            self.phase = Phase.END_STEP

        return available_actions
