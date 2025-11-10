import abc
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
import random

from ability_2 import get_all_creatures
from build_deck import GameCard, Deck
from models.board import Board
from models.combat import Combat
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

    @property
    def instants(self) -> list[GameCard]:
        return [c for c in self.cards if 'Instant' in c.props.card_types]

    @property
    def sorceries(self) -> list[GameCard]:
        return [c for c in self.cards if 'Sorcery' in c.props.card_types]

    def sort_cards(self):
        self.cards.sort(key=lambda x: x.props.casting_weight, reverse=self.sort_pref.value)


@dataclass
class Turn:
    in_turn_player_idx: int
    out_turn_player_idx: int
    has_played_land: bool = False


@dataclass
class Action(ABC):
    player_idx: int

    @abc.abstractmethod
    def play(self) -> None:
        ...

@dataclass
class ActionStack:
    _actions: list[Action] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._actions)

    @property
    def last_actor_idx(self) -> int:
        return self._actions[-1].player_idx

    @property
    def action_on_idx(self) -> int:
        return 1 if self.last_actor_idx == 0 else 0

    @property
    def last_action(self) -> Action:
        return self._actions[-1]

    def add(self, action: Action, gs: "GameState") -> None:
        self._actions.append(action)
        gs.action_on_idx = 1 if gs.action_on_idx == 0 else 0

    def clear(self) -> None:
        self._actions.clear()

@dataclass
class DrawCard(Action):
    deck: Deck
    hand: Hand
    gs: "GameState"

    def __repr__(self) -> str:
        return 'Draw a Card'

    def play(self) -> None:
        self.hand.cards.append(self.deck.cards.pop())
        self.hand.sort_cards()
        self.gs.phase = Phase.CAST

@dataclass
class PlayLand(Action):
    card_in_hand_idx: int
    card: GameCard
    source_hand: Hand
    board: Board
    turn: Turn

    def __repr__(self) -> str:
        return f"Play {self.card.props.name} land to board"

    def play(self) -> None:
        self.board.play_to_board(self.source_hand.cards.pop(self.card_in_hand_idx))
        mana = LAND_MANA_DICT.get(self.card.props.slug)
        if not mana:
            raise NotImplementedError("I can't handle non-basic lands")
        self.board.add_mana(mana, 1)
        self.turn.has_played_land = True


@dataclass
class PlayAura(Action):
    card: GameCard
    target: GameCard
    board: Board
    gs: "GameState"

    def __repr__(self):
        return f"Add aura {self.card.props.name} to {self.target.props.name}"

    def play(self) -> None:
        self.board.pay_casting_cost(self.card.props.casting_cost)
        self.target.enchant_creatures.append(self.card)


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
        self.board.play_to_board(self.source_hand.cards.pop(self.card_in_hand_idx))


@dataclass
class PlaySorceryOrInstant(Action):
    card: GameCard
    source_hand: Hand
    board: Board
    action_stack: ActionStack
    targets: list[GameCard]
    gs: "GameState"

    def __repr__(self) -> str:
        target_text = f", targeting {', '.join([c.props.name for c in self.targets])}" if self.targets else ''
        return f"Play {self.card.props.name} as sorcery/instant{target_text}"

    def play(self) -> None:
        self.board.pay_casting_cost(self.card.props.casting_cost)
        self.source_hand.cards.remove(self.card)
        self.action_stack.add(self, self.gs)

    def accept(self) -> None:
        if self.card.props.slug == 'swords-to-plowshares':
            self.gs.send_to_exile(self.targets[0])
            self.gs.life[self.targets[0].orig_owner_id] += self.targets[0].power
            print(f'Swords to Plowshares accepted; life is now {self.gs.life}')
        elif self.card.props.slug == 'wrath-of-god':
            for t in self.targets:
                self.gs.send_to_exile(t)
            print(f'Wrath of God accepted; all creatures should now be in exile')
        elif self.card.props.slug == 'jump':
            self.targets[0].has_flying = True
            self.gs.effects.append(f"Creature ID#{self.targets[0].id} gains Flying until end of turn")
            print(f"{self.targets[0].props.name} gains Flying until end of turn")
        elif self.card.props.slug == 'creature-bond':
            self.targets[0].enchant_creatures.append(self.card)

@dataclass
class CreatureAttack(Action):
    card: GameCard
    gs: "GameState"

    def __repr__(self) -> str:
        return f"Add {self.card.props.name} to attack"

    def play(self) -> None:
        self.card.tap()
        self.gs.combats.append(Combat(self.gs, self.card))


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
        self.gs.action_on_idx = 1 if self.gs.action_on_idx == 0 else 0


@dataclass
class AssignBlocker(Action):
    blocker: GameCard
    attacker: GameCard
    gs: "GameState"

    def __repr__(self) -> str:
        return f"Block {self.attacker} with {self.blocker}"

    def play(self) -> None:
        for com in self.gs.combats:
            if com.attacker == self.attacker:
                com.blockers.append(self.blocker)


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
class DiscardCard(Action):
    hand: list[GameCard]
    card: GameCard
    gs: "GameState"

    def __repr__(self) -> str:
        return f"Discard {self.card} to graveyard"

    def play(self) -> None:
        self.gs.send_to_graveyard(self.card)
        self.hand.remove(self.card)

@dataclass
class PassTheTurn(Action):
    gs: "GameState"

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.player_turn_idx = 1 if self.gs.player_turn_idx == 0 else 0
        self.gs.action_on_idx = self.gs.player_turn_idx
        self.gs.turn = Turn(self.gs.player_turn_idx, 1 if self.gs.player_turn_idx == 0 else 0)
        self.gs.turn_number += 1
        self.gs.phase = Phase.UNTAP

@dataclass
class AcceptAction(Action):
    action_stack: ActionStack
    gs: "GameState"

    def __repr__(self) -> str:
        return f"Accept {self.action_stack.last_action}"

    def play(self) -> None:
        if isinstance(self.action_stack.last_action, PlaySorceryOrInstant):
            self.action_stack.last_action.accept()
        self.action_stack.clear()
        self.gs.action_on_idx = 1 if self.gs.action_on_idx == 0 else 0

@dataclass
class CounterAction(Action):
    action_stack: ActionStack
    action: Action
    gs: "GameState"

    def __repr__(self) -> str:
        return f"In response to {self.action_stack.last_action}: {self.action}"

    def play(self) -> None:
        self.action_stack.add(self.action, self.gs)
        self.gs.action_on_idx = 1 if self.gs.action_on_idx == 0 else 0


class GameState:
    def __init__(self, player_cnt: int, player_turn_idx: int, decks: list[Deck]):
        self.player_cnt = player_cnt
        self.player_turn_idx = player_turn_idx
        self.decks = decks
        self.life = [20, 20]
        self.action_on_idx: int = self.player_turn_idx
        self.turn = Turn(self.player_turn_idx, 1 if self.player_turn_idx == 0 else 1)
        self.boards: list[Board] = [Board(i) for i in range(self.player_cnt)]
        self.graveyards: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.exiles: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.hands: list[Hand] = [Hand(sort_pref=Hand.SortOrient.L_TO_R) for _ in range(self.player_cnt)]
        self.phase = Phase.UNTAP
        self.action_stack = ActionStack()
        self.game_history: list[tuple[int, Action]] = []  # turn number & Action; appended to in engine.play()
        self.turn_number = 1
        self.combats: list[Combat] = []
        self.effects: list[str] = []
        
        for i in range(self.player_cnt):
            deck = self.decks[i]
            random.shuffle(deck.cards)
            hand = self.hands[i]
            draw(hand.cards, deck.cards, 7)
            hand.sort_cards()

    def get_card_from_boards(self, card_id: int) -> GameCard | None:
        return next((c for b in self.boards for c in b.cards if c.id == card_id), None)

    def _remove_from_board(self, c: GameCard) -> GameCard | None:
        for board in self.boards:
            for card in board.cards:
                if card.id == c.id:
                    board.remove_from_board(c)
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
        if 'Creature' in c.props.card_types:
            c.power = c.props.power
            c.toughness = c.props.toughness
            c.has_flying = 'Flying' in c.props.keyword_abilities
        if 'creature-bond' in [card.props.slug for card in c.enchant_creatures]:
            self.life[c.orig_owner_id] -= c.props.toughness
            print(f"Creature Bond reduces player #{c.orig_owner_id}'s life by {c.props.toughness}")

    def untap(self):
        for c in self.boards[self.player_turn_idx].cards:
            c.untap()
            for turn_num, act in self.game_history:
                if (isinstance(act, PlayNonBasicLandToBoard) and act.card.id == c.id and
                        self.turn_number - turn_num == 2):
                    c.has_summoning_sickness = False

        self.phase = Phase.UPKEEP

    @staticmethod
    def get_card_id_from_effects_list(effect_row: str) -> int:
        return int(effect_row[effect_row.find('ID#') + 4:effect_row.find(' ', effect_row.find('ID#') + 4)])

    def get_available_actions(self, p_id: int) -> list[Action] | None:
        available_actions: list[Action] = []
        deck = self.decks[p_id]
        hand = self.hands[p_id]
        board = self.boards[p_id]

        if len(self.action_stack):
            if p_id != self.player_turn_idx:
                available_actions.append(AcceptAction(p_id, self.action_stack, self))
                playable_cards = [c for c in hand.instants if board.can_card_meet_casting_cost(c)]
                for c in playable_cards:
                    if c.props.slug in ('swords-to-plowshares', 'jump'):
                        targets: list[GameCard] = get_all_creatures(self)
                        for t in targets:
                            available_actions.append(PlaySorceryOrInstant(p_id, c, hand, board,
                                                                          self.action_stack, [t], self))
            else:
                available_actions.append(AcceptAction(p_id, self.action_stack, self))
                playable_cards: list[GameCard] = hand.instants + hand.sorceries
                for c in playable_cards:
                    if c.props.slug in ('swords-to-plowshares', 'jump', 'creature-bond'):
                        targets: list[GameCard] = get_all_creatures(self)
                        for t in targets:
                            available_actions.append(PlaySorceryOrInstant(p_id, c, hand, board,
                                                                          self.action_stack, [t], self))
                    elif c.props.slug in ('wrath-of-god',):
                        targets: list[GameCard] = get_all_creatures(self)
                        available_actions.append(PlaySorceryOrInstant(p_id, c, hand, board,
                                                                      self.action_stack, targets, self))

            return available_actions

        if self.phase == Phase.UNTAP:
            self.untap()
            return

        if self.phase == Phase.UPKEEP:
            self.phase = Phase.DRAW
            return

        if self.phase == Phase.DRAW:
            available_actions.append(DrawCard(p_id, deck, hand, self))
            return available_actions

        if self.phase == Phase.CAST:
            available_actions.append(PassTheTurn(p_id, self))
            # play a land
            if not self.turn.has_played_land:
                available_actions.extend([PlayLand(p_id, i, c, hand, board, self.turn) for i, c in enumerate(hand.cards)
                                         if c.props.is_land])

            # play a non-land card; compare its casting cost to the board to see if it can cast
            for i, c in enumerate(hand.cards):
                if c.props.is_land or not board.can_card_meet_casting_cost(c):
                    continue

                if c.props.is_permanent:
                    if 'Aura' in c.props.card_sub_types:  # play Enchant Creature
                        ...
                    else:  # play to board
                        available_actions.append(PlayNonBasicLandToBoard(p_id, i, c, hand, board))
                else:  # add to stack
                    opp_board = self.boards[1] if p_id == 0 else self.boards[0]

                    if c.props.slug in ('swords-to-plowshares', 'jump'):
                        targets: list[GameCard] = get_all_creatures(self)
                        for t in targets:
                            available_actions.append(PlaySorceryOrInstant(p_id, c, hand, board,
                                                                          self.action_stack, [t], self))
                    elif c.props.slug in ('wrath-of-god', ):
                        targets: list[GameCard] = get_all_creatures(self)
                        available_actions.append(PlaySorceryOrInstant(p_id, c, hand, board,
                                                                      self.action_stack, targets, self))

            # declare combat
            for c in board.cards:
                if c.can_attack and not c.has_summoning_sickness:
                    available_actions.append(BeginCombat(p_id, self))

        if self.phase == Phase.DECLARE_ATTACKERS:
            # add attackers
            for c in board.cards:
                if c not in [com.attacker for com in self.combats] and c.can_attack and not c.has_summoning_sickness:
                    available_actions.append(CreatureAttack(p_id, c, self))

            # finish declaring attackers; move to declare blockers
            if self.combats:
                available_actions.append(FinishDeclaringAttackers(p_id, self))

        if self.phase == Phase.DECLARE_BLOCKERS:
            already_assigned_blockers = [c for com in self.combats for c in com.blockers]
            remaining_blockers = [c for c in self.boards[self.action_on_idx].available_blockers
                                  if c not in already_assigned_blockers]
            for blocker in remaining_blockers:
                for com in self.combats:
                    available_actions.append(AssignBlocker(self.action_on_idx, blocker, com.attacker, self))
            available_actions.append((FinishBlocking(self.action_on_idx, self)))

        if self.phase == Phase.END_STEP:
            available_actions.append(PassTheTurn(p_id, self))
            self.phase = Phase.DISCARD
            return

        if self.phase == Phase.DISCARD:
            hand = self.hands[self.player_turn_idx]
            if len(hand.cards) > 7:
                for c in hand.cards:
                    available_actions.append(DiscardCard(self.player_turn_idx, hand.cards, c, self))
            else:
                self.phase = Phase.CREATURES_HEAL
                return

        if self.phase == Phase.CREATURES_HEAL:
            for e in self.effects[:]:
                print(type(e), e)
                if 'Combat Damage' in e:
                    card_id = self.get_card_id_from_effects_list(e)  # the card dealing the damage
                    damage = int(e[e.find('deals ') + 6:e.find('damage') - 1])
                    card = self.get_card_from_boards(card_id)
                    if card:
                        card.power += damage
                    card_id = int(e[e.find('to creature ID#') + 15:e.find(' ', e.find('to creature ID#') + 15)])  # card receiving the damage
                    card = self.get_card_from_boards(card_id)
                    if card:
                        card.toughness += damage
                    self.effects.remove(e)
            self.phase = Phase.END_TURN_EFFECTS
            return

        if self.phase == Phase.END_TURN_EFFECTS:
            for e in self.effects[:]:
                card_id = self.get_card_id_from_effects_list(e)
                card = self.get_card_from_boards(card_id)
                if 'until end of turn' in e:
                    if 'gains Flying' in e:
                        card.has_flying = 'Flying' in card.props.keyword_abilities
                        self.effects.remove(e)
                        print(f'{card.props.name} no longer has Flying')
            self.phase = Phase.PASS_THE_TURN
            return

        if self.phase == Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES:
            #  TODO: attackers & blockers have been declared
            #   this would normally allow players to cast instants, but let's skip that and instead ...
            #   go to FIRST_STRIKE_DAMAGE
            self.phase = Phase.FIRST_STRIKE_DAMAGE
            for com in self.combats:
                com.handle_first_strike_damage()
            self.phase = Phase.COMBAT_DAMAGE
            for com in self.combats:
                com.handle_combat_damage()
            self.phase = Phase.COMBAT_END
            for com in self.combats:
                com.end_combat(self)
            self.combats.clear()
            self.phase = Phase.END_STEP

        return available_actions

    def make_move(self, action: Action):
        ...


# TODO NEXT:
#  accepting an instant produces this:
#    File "/Users/Bernacki_Laptop/PycharmProjects/magicnacki/game_state.py", line 227, in play
#     self.source_hand.cards.remove(self.card)
