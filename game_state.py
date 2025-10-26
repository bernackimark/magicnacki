import abc
from abc import ABC
from itertools import combinations
from dataclasses import dataclass, field
from enum import Enum
import random

from build_deck import GameCard, Deck
from card import COLOR_LETTERS
from phase_fsm import Phase

LAND_MANA_DICT = {'island': 'U', 'forest': 'G', 'swamp': 'B', 'mountain': 'R', 'plains': 'W'}

def draw(dest_pile: list[GameCard], source_pile: list[GameCard], card_cnt: int):
    for i in range(card_cnt):
        dest_pile.append(source_pile.pop(0))


@dataclass
class Hand:
    class SortOrient(Enum):
        L_TO_R = False
        R_TO_L = True
    cards: list[GameCard] = field(default_factory=list)
    sort_pref: SortOrient = SortOrient.R_TO_L

    def sort_cards(self):
        self.cards.sort(key=lambda x: x.props.casting_weight, reverse=self.sort_pref.value)


@dataclass
class Turn:
    in_turn_player_idx: int
    out_turn_player_idx: int
    has_played_land: bool = False


@dataclass
class Board:
    player_idx: int
    cards: list[GameCard] = field(default_factory=list)
    attacking_creatures: list[GameCard] = field(default_factory=list)

    @property
    def available_mana(self) -> dict:
        # TODO: needs to be thought thru; needs to handle cards that can spontaneously add mana
        d = {color: 0 for color in COLOR_LETTERS}
        d['C'] = 0
        d['W'] = sum([1 for c in self.cards if c.props.slug == 'plains' and not c.is_tapped])
        d['U'] = sum([1 for c in self.cards if c.props.slug == 'island' and not c.is_tapped])
        d['B'] = sum([1 for c in self.cards if c.props.slug == 'swamp' and not c.is_tapped])
        return d

    @property
    def available_mana_cnt(self) -> int:
        return sum([v for v in self.available_mana.values()])

    @property
    def available_blockers(self) -> list[GameCard]:
        return [c for c in self.cards if c.can_block and not c.is_tapped]

    def can_card_meet_casting_cost(self, c: GameCard) -> bool:
        for color_code, color_cnt in c.props.casting_dict.items():
            if color_code != 'C' and color_cnt > self.available_mana[color_code]:
                return False
            if color_code == 'C' and c.props.casting_weight > self.available_mana_cnt:
                return False
        return True

    def add_mana(self, mana_color: str, cnt: int) -> None:
        self.available_mana[mana_color] += cnt

    def subtract_mana(self, mana_color: str, cnt: int) -> None:
        self.available_mana[mana_color] -= cnt

    def pay_casting_cost(self, casting_cost: str) -> None:
        for _ in casting_cost:
            untapped_lands = [c for c in self.cards if c.props.is_land and not c.is_tapped]
            untapped_lands[0].tap()

    def add_defender(self, attacker: GameCard):
        ...


@dataclass
class Action(ABC):
    player_idx: int

    @abc.abstractmethod
    def play(self) -> None:
        ...


@dataclass
class ActionStack:
    # TODO: think "FIFO"
    actions: list[Action] = field(default=list)


@dataclass
class PlayLand(Action):
    card_in_hand_idx: int
    card: GameCard
    source_hand: Hand
    board: Board

    def __repr__(self) -> str:
        return f"Play {self.card.props.name} land to board"

    def play(self) -> None:
        self.board.cards.append(self.source_hand.cards.pop(self.card_in_hand_idx))
        mana = LAND_MANA_DICT.get(self.card.props.slug)
        if not mana:
            raise NotImplementedError("I can't handle non-basic lands")
        self.board.add_mana(mana, 1)


@dataclass
class PlayNonBasicLandToBoard(Action):
    card_in_hand_idx: int
    card: GameCard
    source_hand: Hand
    board: Board

    def __repr__(self) -> str:
        return f"Play {self.card.props.name} creature to board"

    def play(self) -> None:
        self.board.pay_casting_cost(self.card.props.casting_cost)
        self.board.cards.append(self.source_hand.cards.pop(self.card_in_hand_idx))
        # TODO: find land card(s) to tap


@dataclass
class PlaySorceryOrInstant(Action):
    card_in_hand_idx: int
    card: GameCard
    source_hand: Hand
    board: Board
    action_stack: ActionStack
    targets: list[GameCard]

    def __repr__(self) -> str:
        target_text = f", targeting {', '.join([c.props.name for c in self.targets])}" if self.targets else ''
        return f"Play {self.card.props.name} as sorcery/instant{target_text}"

    def play(self) -> None:
        self.action_stack.actions.append(self)
        self.source_hand.cards.pop(self.card_in_hand_idx)


@dataclass
class CreatureAttack(Action):
    card: GameCard
    board: Board

    def __repr__(self) -> str:
        return f"Add {self.card.props.name} to attack"

    def play(self) -> None:
        self.card.tap()
        self.board.attacking_creatures.append(self.card)


@dataclass
class BeginCombat(Action):
    gs: "GameState"

    def __repr__(self) -> str:
        return "Begin Combat"

    def play(self) -> None:
        self.gs.phase = Phase.DECLARE_ATTACKERS


@dataclass
class FinishDeclaringAttackers(Action):
    gs: "GameState"

    def __repr__(self) -> str:
        return "Done Declaring Attackers"

    def play(self) -> None:
        self.gs.phase = Phase.DECLARE_BLOCKERS
        self.gs.combats = [[c, []] for c in self.gs.boards[self.gs.player_turn_idx].attacking_creatures]
        self.gs.action_on_idx = 1 if self.gs.action_on_idx == 0 else 0


@dataclass
class AssignBlocker(Action):
    blocker: GameCard
    attacker: GameCard
    gs: "GameState"

    def __repr__(self) -> str:
        return f"Block {self.attacker} with {self.blocker}"

    def play(self) -> None:
        for i, (attacker, blockers) in enumerate(self.gs.combats):
            if attacker == self.attacker:
                blockers.append(self.blocker)


@dataclass
class FinishBlocking(Action):
    gs: "GameState"

    def __repr__(self) -> str:
        return f"Finish Blocks"

    def play(self) -> None:
        self.gs.phase = Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES

@dataclass
class MoveToEndStep(Action):
    gs: "GameState"

    def __repr__(self) -> str:
        return "Moving to End Step"

    def play(self) -> None:
        self.gs.phase = Phase.END_STEP


@dataclass
class PassTheTurn(Action):
    gs: "GameState"

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.phase = Phase.UNTAP
        self.gs.player_turn_idx = 1 if self.gs.player_turn_idx == 0 else 0


@dataclass
class GameState:
    player_cnt: int
    player_turn_idx: int
    decks: list[Deck]
    boards: list[Board] = field(default_factory=list)
    graveyards: list[list] = field(default_factory=list)
    hands: list[Hand] = field(default_factory=list)
    phase = Phase.UNTAP
    action_stack = ActionStack()
    game_history: list[tuple[int, Action]] = field(default_factory=list)
    turn_number = 0
    has_played_land = False
    action_on_idx: int = field(default=None)
    combats: list[list[GameCard: list[GameCard]]] = field(default_factory=list)

    def __post_init__(self):
        for i in range(self.player_cnt):
            self.boards.append(Board(i))
            self.graveyards.append([])
            deck = self.decks[i]
            random.shuffle(deck.cards)
            hand = Hand(sort_pref=Hand.SortOrient.L_TO_R)
            self.hands.append(hand)
            draw(hand.cards, deck.cards, 7)
            hand.sort_cards()
        self.action_on_idx = self.player_turn_idx

    def get_available_actions(self, p_id: int):
        available_actions: list[Action] = []
        hand = self.hands[p_id]
        board = self.boards[p_id]

        available_actions.append(PassTheTurn(p_id, self))

        if self.phase == Phase.CAST:
            # play a land
            if not self.has_played_land:
                available_actions.extend([PlayLand(p_id, i, c, hand, board) for i, c in enumerate(hand.cards)
                                         if c.props.is_land])

            # play a non-land card; compare its casting cost to the board to see if it can cast
            for i, c in enumerate(hand.cards):
                if c.props.is_land or not board.can_card_meet_casting_cost(c):
                    continue

                if c.props.is_permanent:  # play to board
                    available_actions.append(PlayNonBasicLandToBoard(p_id, i, c, hand, board))
                else:  # add to stack
                    opp_board = self.boards[1] if p_id == 0 else self.boards[0]
                    available_actions.append(PlaySorceryOrInstant(p_id, i, c, hand, board,
                                                                  self.action_stack, opp_board.cards))

            # declare combat
            for c in board.cards:
                if c.can_attack and not c.has_summoning_sickness:
                    available_actions.append(BeginCombat(p_id, self))

        if self.phase == Phase.DECLARE_ATTACKERS:
            # add attackers
            for c in board.cards:
                if c not in board.attacking_creatures and c.can_attack and not c.has_summoning_sickness:
                    available_actions.append(CreatureAttack(p_id, c, board))

            # finish declaring attackers; move to declare blockers
            if board.attacking_creatures:
                available_actions.append(FinishDeclaringAttackers(p_id, self))

        if self.phase == Phase.DECLARE_BLOCKERS:
            already_assigned_blockers = [c for blocking_combo in self.combats for c in blocking_combo]
            remaining_blockers = [c for c in self.boards[self.action_on_idx].available_blockers if c not in already_assigned_blockers]
            for blocker in remaining_blockers:
                for attacker, _ in self.combats:
                    available_actions.append(AssignBlocker(self.action_on_idx, blocker, attacker, self))

        if self.phase == Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES:
            ...
            #  TODO: attackers & blockers have been declared
            #   this would normally allow players to cast instants, but let's skip that and instead ...
            #   go to FIRST_STRIKE_DAMAGE

        return available_actions

    def make_move(self, action: Action):
        ...


