import random
from typing import Callable, Optional

from action_stack import ActionStack
from build_deck import Deck
from card_filter import CardFilter
from constants import BASIC_LAND_MANA_PRODUCED
from models.actions.activate_ability import ActivateAbility
from models.actions.base import Action
from models.actions.cast import CastToBoard, CastToTargetAddToStack, CastCounter
from models.actions.combat import CreatureAttack, BeginCombat, FinishDeclaringAttackers, AssignBlocker, FinishBlocking, \
    AssignCombatDamage
from models.actions.draw_discard import DrawCard, DiscardCard
from models.actions.end_step_pass_turn import MoveToEndStep, PassTheTurn
from models.actions.stack_accept_counter import AcceptAction
from models.activated_ability import add_activated_abilities
from models.damage import DamageEvent, PreventNextDamage
from models.effects.can_block import can_block_base_rule
from models.effects.global_ import GlobalEffect
from models.game_card import GameCard
from models.board import Board
from models.combat import Combat
from models.hand import Hand
from models.mana import ManaPool
from models.turn import Turn
from phase_fsm import Phase
from utils import flip


class GameState:
    def __init__(self, player_cnt: int, player_turn_idx: int, decks: list[Deck]):
        self.player_cnt = player_cnt
        self.player_turn_idx = player_turn_idx
        self.decks = decks
        for d in self.decks:
            add_activated_abilities(d.cards)
            for c in d.cards:
                c.game_state = self
        self.decks_all_cards = self.decks.copy()
        self.life = [20, 20]
        self.action_on_idx: int = self.player_turn_idx
        self.turn = Turn(self.player_turn_idx, flip(self.player_turn_idx))
        self.boards: list[Board] = [Board(i) for i in range(self.player_cnt)]
        self.graveyards: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.exiles: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
        self.hands: list[Hand] = [Hand(sort_pref=Hand.SortOrient.L_TO_R) for _ in range(self.player_cnt)]
        self.mana_pools: list[ManaPool] = [ManaPool(self, i) for i in range(self.player_cnt)]
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

        self.global_effects: list[tuple[GameCard, GlobalEffect]] = []

        # registries for side effects that are not captured in card effects
        # life-loss registry uses (cond, effect) tuples similar to your TAP_REGISTRY style
        self.life_loss_registry: list[tuple[Callable, Callable]] = [
            # backfire: if the source has an aura with slug 'backfire', deal the same life loss to opponent
            (lambda gs, p_id, amt, source: any(a.props.slug == "backfire" for a in source.modifiers.auras),
             lambda gs, p_id, amt, source: gs._apply_opponent_life_loss(p_id, amt))
        ]

        # default leave handlers: ensure cleanup always occurs even if no slug specific handler
        self.leave_default_handlers: list[Callable] = [lambda gs, c, tgt: c.clear_all_mods()]

        self.damage_preventions: list[PreventNextDamage] = []
        self.end_of_turn_effects: list = []

    # Event Dispatcher
    def trigger(self, event: str, card: GameCard, target: Optional[GameCard] = None):
        """Dispatch an event (string) to the card's effects; event in {'cast','upkeep','tap','untap','leave'}"""
        for e in card.effects:
            if e.event == event:
                e.resolve(self, card, target)

    def on_query(self, event: str, card: GameCard, **kwargs):
        """Ask all effects whether this event is permitted. If any effect returns False, the action is denied.
        If none return False, action is allowed."""
        # Check local effects on the card
        for eff in card.effects:
            r = eff.on_query(self, event, card, **kwargs)
            if r is False:
                return False

        # Check global effects
        for card, eff in self.global_effects:
            pass  # TODO: update this

        return True

    def can_attack(self, card: GameCard) -> bool:
        """Base rules, card effects (such as MAPPING['sea-serpent']: lambda c: IslandhomeEffect(), global effects."""
        # Base rules first
        if (not card.props.is_creature or card.has_summoning_sickness or card.is_tapped
                or 'Defender' in card.keyword_abilities or card in [combat.attacker for combat in self.combats]):
            return False

        # Ask global effects and card effects
        global_effects = [eff for card, eff in self.global_effects]
        for effect in card.effects + global_effects:
            result = effect.on_query(self, "can_attack", card=card)
            if result is False:  # hard veto
                return False

        return True

    def can_block(self, blocker: GameCard, attacker: GameCard):
        # Base rules first
        if can_block_base_rule().on_query(self, 'can_block', card=blocker, attacker=attacker) is False:
            return False

        # Ask global effects, card effects, and card's aura effects
        global_effects = [eff for card, eff in self.global_effects]
        for effect in blocker.effects + global_effects + [a.effects for a in blocker.modifiers.auras]:
            result = effect.on_query(self, 'can_block', card=blocker, attacker=attacker)
            if result is False:  # hard veto
                return False

        return True

    def _apply_opponent_life_loss(self, p_id: int, amt: int):
        """Helper for self.life_loss_registry"""
        opp = flip(p_id)
        self.life[opp] -= amt

    # Pile Helpers & card movement
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

    # --- DAMAGE ---
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int, is_combat: bool = False):
        event = DamageEvent(source, amount, target, is_combat)

        # 1. Give all effects a chance to prevent/redirect
        self.trigger_damage_prevention(event)

        # 2. Apply remaining damage
        if event.remaining <= 0:
            return
        if isinstance(target, GameCard):
            target.combat_damage_received += event.remaining
        else:
            self.decrement_life(target, event.remaining, source)

    def trigger_damage_prevention(self, event: DamageEvent):
        """Give all prevention / replacement effects a chance to modify the damage event in this order:
        1. Card-specific continuous effects; 2. Global continuous effects; 3. Temporary 'next damage' shields"""

        for card in self.card_filter.in_play().result():
            for eff in card.effects:
                eff.on_damage(self, event)

        for _, eff in self.global_effects:
            eff.on_damage(self, event)

        for p in self.damage_preventions:
            p.apply(event)
            if p.amt <= 0:
                self.damage_preventions.remove(p)

    # --- CARD MOVEMENT ---
    def remove_from_board(self, c: GameCard) -> None:
        """Trigger leave event for card (ex Crusade, Castle); remove card from board; remove all auras from board"""
        self.trigger('leave', c)
        board = self.boards[c.orig_owner_id]
        board.remove_from_board(c)
        print(f"{c} has been removed from the board")
        for a in c.modifiers.auras:
            board.remove_from_board(a)
            print(f"{a} has been removed from the board")

    def send_to_graveyard_from_play(self, c: GameCard):
        """Send card to graveyard; send all auras to graveyard"""
        self.remove_from_board(c)
        self.graveyards[c.orig_owner_id].append(c)
        print(f"{c} has been sent to graveyard")
        for a in c.modifiers.auras:
            self.graveyards[c.orig_owner_id].append(a)
            print(f"{a} has been sent to graveyard")
        self._send_to_graveyard_or_exile(c)

    def send_to_graveyard(self, c: GameCard):
        # TODO: reconcile send_to_gy_from_play & send_to_gy
        self.graveyards[c.orig_owner_id].append(c)
        print(f'{c} has been sent to the graveyard')
        self._send_to_graveyard_or_exile(c)

    def send_to_exile(self, c: GameCard):
        self.exiles[c.orig_owner_id].append(c)
        print(f'{c} has been exiled')
        self._send_to_graveyard_or_exile(c)

    def send_to_exile_from_play(self, c: GameCard):
        self.remove_from_board(c)
        self.exiles[c.orig_owner_id].append(c)
        print(f'{c} has been exiled')
        for a in c.modifiers.auras:
            self.exiles[c.orig_owner_id].append(a)
            print(f'{a} has been exiled')
        self._send_to_graveyard_or_exile(c)

    def _send_to_graveyard_or_exile(self, c: GameCard):
        """Remove card from board if not done yet;
        clear all attached_to relationships & clear .auras(), .pt_modifiers(), etc"""
        # if board removal slipped through the cracks, do that here
        board = self.boards[c.orig_owner_id]
        if c in board.cards:
            board.remove_from_board(c)
        c.clear_all_mods()  # clear all attached_to relationships

    def return_to_hand(self, c: GameCard):
        hand = self.hands[c.orig_owner_id]
        hand.cards.append(c)
        for a in c.modifiers.auras:
            self.send_to_graveyard_from_play(a)
        c.clear_all_mods()
        hand.sort_cards()

    def return_to_hand_from_board(self, c: GameCard):
        board = self.boards[c.orig_owner_id]
        board.remove_from_board(c)
        self.return_to_hand(c)

    # Life Operations; using Registry Pattern
    def increment_life(self, p_id: int, amt: int):
        print(f"Increasing player #{p_id}'s life by {amt}. Life is now at {self.life}")
        self.life[p_id] += amt

    def decrement_life(self, p_id: int, amt: int, source: GameCard):
        """Reduce player life; lookup life loss condition in self.life_loss_registry; check for end game condition"""
        self.life[p_id] -= amt
        print(f"Reducing player #{p_id}'s life by {amt}. Life is now at {self.life}")

        # run life-loss registry conditions (pattern: (cond, effect))
        for cond, effect in self.life_loss_registry:
            if cond(self, p_id, amt, source):
                effect(self, p_id, amt, source)

        if self.life[p_id] <= 0 < self.life[flip(p_id)]:
            print(f"Player #{p_id} has lost")
            self.is_game_over = True
        elif self.life[p_id] <= 0 and self.life[flip(p_id)] <= 0:
            print(f"Both players have lost")
            self.is_game_over = True

    def apply_tap_effects(self, c: GameCard):
        self.trigger('tap', c)

    def apply_untap_effects(self, c: GameCard):
        self.trigger('untap', c)

    def untap(self):
        """Untap all cards on in-turn player's board; remove summoning sickness"""
        for c in self.boards[self.player_turn_idx].cards:
            for turn_num, act in self.game_history:
                if isinstance(act, CastToBoard) and act.card.id == c.id and self.turn_number - turn_num == 2:
                    c.has_summoning_sickness = False
            if not c.is_tapped:
                continue
            c.untap(self)

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility] = []

        for ability in c.abilities:
            if not ability.can_activate(self):
                continue
            if c.has_summoning_sickness:
                continue

            if ability.target_filter is None:  # janky solution; auras have target_filter = None
                actions.append(ActivateAbility(self.action_on_idx, self, ability, c.attached_to))
                continue

            targets = ability.target_filter(self, c)
            # Returns None | GameCard | list[GameCard] | tuple[int] (targets p_id's) | int (targets a single p_id)
            print(f"{c=}, {ability=}, {targets=}")

            # No target needed → create a single action
            if targets is None:
                actions.append(ActivateAbility(self.action_on_idx, self, ability, None))
                continue

            # I need at least one target, but I don't have any
            elif isinstance(targets, list) and targets == []:
                continue

            # Targeting multiple player indices
            elif targets == (0, 1) or targets == (1, 0):
                for t in targets:
                    actions.append(ActivateAbility(self.action_on_idx, self, ability, t))

            # Targeting a single player index
            elif targets == 0 or targets == 1:
                actions.append(ActivateAbility(self.action_on_idx, self, ability, targets))

            # Targeting a single GameCard
            elif isinstance(targets, GameCard):
                actions.append(ActivateAbility(self.action_on_idx, self, ability, targets))

            # I need a target and got a valid list of GameCards
            elif isinstance(targets, list) and isinstance(targets[0], GameCard):
                for t in targets:
                    actions.append(ActivateAbility(self.action_on_idx, self, ability, t))

            else:
                raise ValueError(f"Broke assigning target to this Activated Ability: {ability.card=} {targets=}")
        return actions

    def get_available_actions(self, p_id: int) -> list[Action] | None:
        """Determine all legal actions available to player_id in the current phase ...
         (casting, activating abilities, combat, phase-specific actions, etc.)"""
        available_actions: list[Action] = []
        hand = self.hands[p_id]
        board = self.boards[p_id]

        # Helper: add all activated abilities for all phases
        def add_activated_abilities_from_board() -> list[ActivateAbility] | list[None]:
            actions: list[ActivateAbility] = []
            for card in board.cards:
                actions.extend(self.get_available_activated_abilities(card))
                for aura in card.modifiers.auras:
                    if not isinstance(aura, GameCard):  # some auras can be KWAModifier/PTModifiers (this is confusing)
                        continue
                    actions.extend(self.get_available_activated_abilities(aura))
            return actions

        # if there is something on the stack, respond & resolve, don't seek out other available actions
        if len(self.action_stack):
            available_actions.append(AcceptAction(p_id, self))

            # Check instants (or other spells allowed to respond)
            allowed_cards = hand.instants + hand.sorceries if p_id == self.player_turn_idx else hand.sorceries
            playable_cards: list[GameCard] = [c for c in allowed_cards if self.mana_pools[p_id].can_pay(c.casting_cost)]

            for c in playable_cards:
                # Handle counterspells separately
                if c.props.slug in ('counterspell',):
                    target: Action = self.action_stack.last_action
                    available_actions.append(CastCounter(p_id, self, c, target))
                    continue

                # Handle other spells
                target_cards = c.get_cast_targets(self)
                if not target_cards:
                    available_actions.append(CastToTargetAddToStack(p_id, self, c, None))
                    continue
                for t in target_cards:
                    available_actions.append(CastToTargetAddToStack(p_id, self, c, t))

                # Activated abilities can also respond
                available_actions.extend(add_activated_abilities_from_board())

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
                self.trigger('upkeep', c)
                for a in c.modifiers.auras:
                    if not isinstance(a, GameCard):  # KWAModifiers/PTModifiers are auras but aren't actually GameCards
                        continue
                    self.trigger('upkeep', a)
            self.phase = Phase.DRAW
            return

        if self.phase == Phase.DRAW:
            return [DrawCard(p_id, self)]

        if self.phase == Phase.CAST:
            available_actions.append(MoveToEndStep(p_id, self))

            # cast cards from hand
            for c in hand.cards:
                if not self.mana_pools[p_id].can_pay(c.casting_cost):
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

            # activate abilities
            available_actions.extend(add_activated_abilities_from_board())

            # declare combat
            if any(self.can_attack(card) for card in board.cards):
                available_actions.append(BeginCombat(p_id, self))

        if self.phase == Phase.DECLARE_ATTACKERS:
            for c in board.cards:
                if self.can_attack(c):
                    available_actions.append(CreatureAttack(p_id, self, c))

            # finish declaring attackers; move to declare blockers
            if self.combats:
                available_actions.append(FinishDeclaringAttackers(p_id, self))

        if self.phase == Phase.DECLARE_BLOCKERS:
            remaining_blockers = [c for c in self.boards[self.action_on_idx].available_blockers
                                  if c not in [c for com in self.combats for c in com.blockers]]
            for blocker in remaining_blockers:
                for com in self.combats:
                    if self.can_block(blocker, com.attacker):
                        available_actions.append(AssignBlocker(self.action_on_idx, self, blocker, com.attacker))

            # Activated abilities allowed during blockers (instant-speed)
            available_actions.extend(add_activated_abilities_from_board())

            available_actions.append((FinishBlocking(self.action_on_idx, self)))

        if self.phase == Phase.END_STEP:
            for c in self.card_filter.in_play().result():
                c.modifiers.clear_temps()
            self.phase = Phase.DISCARD
            return

        if self.phase == Phase.DISCARD:
            if len(hand.cards) > 7:
                for c in hand.cards:
                    available_actions.append(DiscardCard(self.player_turn_idx, self, c))
            else:
                self.phase = Phase.CREATURES_HEAL

        if self.phase == Phase.CREATURES_HEAL:
            for deck in self.decks_all_cards:
                for c in deck.cards:
                    c.combat_damage_dealt = 0
                    c.combat_damage_received = 0
            self.phase = Phase.END_TURN_EFFECTS

        if self.phase == Phase.END_TURN_EFFECTS:
            # Expire all temporary damage prevention
            self.damage_preventions.clear()
            # Clear temp modifiers
            for d in self.decks_all_cards:
                for c in d.cards:
                    c.modifiers.clear_temps()
            # Empty mana pools
            for pool in self.mana_pools:
                pool.clear_floating()
            # Reset all activated ability counts to 0 (ex: fire-drake {R}: +1/+0; Activate only once each turn.)
            for c in self.card_filter.in_play().result():
                for aa in c.abilities:
                    aa.activated_cnt_this_turn = 0
            self.phase = Phase.PASS_THE_TURN
            return

        if self.phase == Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES:
            # resolve all combat & instant-speed actions
            # Activated abilities allowed after blockers have all been declared (instant-speed)
            available_actions.extend(add_activated_abilities_from_board())

            available_actions.append((AssignCombatDamage(self.action_on_idx, self)))

        if self.phase == Phase.ASSIGN_COMBAT_DAMAGE:
            self.phase = Phase.FIRST_STRIKE_DAMAGE
            self.phase = Phase.COMBAT_DAMAGE
            for com in self.combats:
                com.handle_damage()
            self.phase = Phase.COMBAT_END
            self.combats.clear()
            self.phase = Phase.END_STEP

        return available_actions


# TODO:
#  leave.py: should there just be a common on_leave so when card leaves, all mods for which it's the source are removed?

# TODO:
#  - When deciding which mana to tap, as a strategy, tap colorless mana where possible

# TODO:
#  Unify get_cast_targets() & ActivatedAbility.target_filter:
#  - when casting, i use CAST_TARGETS look-up which maps to a lambda function
#  - when activating, i use a lambda function in the creation of the ActivatedAbility

# TODO:
#  Build a CardUniverseFilter (modeled after CardFilter)
#  - helpful when I'm trying to figure out what are good cards to test
#  - would be helpful to the User when Building a Deck

# TODO:
#  Aura storage location
#  - Right now:
#     for c in board.cards:
#        for a in c.auras:
#  - Should auras & mods just be played to the board of the card owner?
#    There's already a tie back to its host via .attached_to
