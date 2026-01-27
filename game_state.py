import random
from collections import defaultdict
from typing import Callable, Optional

from action_stack import ActionStack
from build_deck import Deck
from card_filter import CardFilter
from models.actions.activate_ability import ActivateAbility
from models.actions.base import Action
from models.actions.cast import CastToBoard, CastToTargetAddToStack, CastCounter
from models.choice_actions.base import ChoiceAction
from models.actions.tap_untap import UntapCardStackPop, LeaveTapped
from models.actions.combat import CreatureAttack, BeginCombat, FinishDeclaringAttackers, AssignBlocker, FinishBlocking, \
    AssignCombatDamage
from models.actions.draw_discard import DrawCard, DiscardCard, MoveToDrawPhase
from models.actions.end_step_pass_turn import MoveToEndStep, PassTheTurn
from models.actions.stack_accept_counter import AcceptAction
from models.damage import DamageEvent, PreventNextDamage
from models.effects.base import Effect
from models.effects.combat import can_block_base_rule
from models.effects.global_ import GlobalEffect
from models.events.base import Event
from models.events.events_all import EndStepEvent
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
            for c in d.cards:
                c.game_state = self
        self.decks_all_cards = self.decks.copy()
        self.life = [20, 20]
        self._poison_counters = [0, 0]
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

        self.global_effects: list[tuple[GameCard, GlobalEffect, bool]] = []  # bool is for expires_at_end_of_turn

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
        self.end_step_funcs: list[Callable] = []
        self.cards_that_died_this_turn: list[GameCard] = []

        # --- event registry for new system ---
        # key = Event subclass, value = list of (effect, source_card) tuples
        self._event_listeners: dict[type, list[tuple[Effect, GameCard]]] = defaultdict(list)

    # --- NEW SYSTEM ---
    def register_effect(self, effect: Effect, source_card: GameCard):
        """Store the effect + source card tuple for later event emission."""
        if effect.listens_to:
            self._event_listeners[effect.listens_to].append((effect, source_card))

    def unregister_effects(self, card: GameCard):
        """Remove any event listeners tied to this card."""
        for event_type, effect_list in self._event_listeners.items():
            # Keep only effects whose source_card is not the leaving card
            self._event_listeners[event_type] = [
                (eff, source_card) for eff, source_card in effect_list
                if source_card != card
            ]

    def emit(self, event: Event):
        """Call all effects listening to a certain type of event (ex: EndStepEvent)"""
        for eff, source_card in self._event_listeners[type(event)]:
            eff.resolve(self, source_card, getattr(event, 'target', None))

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
        global_effects = [eff for _, eff, _ in self.global_effects]
        for effect in card.effects + global_effects:
            result = effect.on_query(self, "can_attack", card=card)
            if result is False:  # hard veto
                return False

        return True

    def can_block(self, blocker: GameCard, attacker: GameCard):
        # Base rules first
        if can_block_base_rule().on_query(self, 'can_block', card=blocker, attacker=attacker) is False:
            print(f"{blocker} can't block {attacker}")
            return False

        # Ask global effects, card effects, and card's aura effects
        global_effects = [eff for _, eff, _ in self.global_effects]
        for eff in blocker.effects + global_effects + [a.effects for a in blocker.modifiers.auras]:
            print(blocker, attacker, eff)
            result = eff.on_query(self, 'can_block', card=blocker, attacker=attacker)
            if result is False:  # hard veto
                return False
        for eff in attacker.effects + global_effects + [a.effects for a in attacker.modifiers.auras]:
            result = eff.on_query(self, 'can_be_blocked', card=attacker, blocker=blocker)
            if result is False:  # hard veto
                return False
        return True

    def _apply_opponent_life_loss(self, p_id: int, amt: int):
        """Helper for self.life_loss_registry"""
        opp = flip(p_id)
        self.life[opp] -= amt

    @property
    def poison_counters(self) -> list[int]:
        return self._poison_counters

    def add_poison_counter(self, p_idx: int, cnt: int = 1):
        self._poison_counters[p_idx] += cnt
        if self._poison_counters[p_idx] >= 10:
            print(f"Player #{p_idx} has lost")
            self.is_game_over = True

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
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int,
                     is_combat: bool = False):
        """Creates DamageEvent, triggers damage preventions, adds .combat_damage_received to card,
        decrements life to player, handles Trample combat damage"""
        event = DamageEvent(source, amount, target, is_combat)

        # 1. Give all effects a chance to prevent/redirect
        self.trigger_damage_prevention(event)

        # 2. Apply remaining damage
        if event.remaining <= 0:
            return
        if is_combat and 'Trample' in source.keyword_abilities and isinstance(target, GameCard):
            damage_to_card = target.toughness
            target.combat_damage_received += damage_to_card
            damage_to_player = event.remaining - damage_to_card
            self.decrement_life(target.orig_owner_id, damage_to_player, source)
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
                if eff.event != 'on_damage':
                    break
                eff.resolve(self, event, card)

        for card, eff, _ in self.global_effects:
            eff.resolve(self, event, card)

        for p in list(self.damage_preventions):
            if event.remaining <= 0:
                break

            prevented = p.apply(event)

            if prevented > 0:
                event.prevented += prevented
                target_text = p.target_card.props.name if p.target_card else f'Player #{p.target_player}'
                print(f"{p.preventer_card.props.name} prevents {prevented} damage to {target_text}")

            if p.remaining is not None and p.remaining <= 0:
                self.damage_preventions.remove(p)

    # --- CARD MOVEMENT ---
    def remove_from_board(self, c: GameCard) -> None:
        """Trigger leave event for card (ex Crusade, Castle); remove card from board; remove all auras from board"""
        self.trigger('leave', c)
        board = self.boards[c.orig_owner_id]
        board.remove_from_board(c)
        print(f"{c} has been removed from the board")
        for a in c.modifiers.auras:
            self.trigger('leave', a) if isinstance(a, GameCard) else self.trigger('leave', a.card)
            board.remove_from_board(a)
            print(f"{a} has been removed from the board")

        # --- NEW EVENT EMISSION SYSTEM ---
        # Remove all registered Event-based effects
        self.unregister_effects(c)

    def send_to_graveyard_from_play(self, c: GameCard):
        """Send card to graveyard; send all card's auras to graveyard"""
        self.remove_from_board(c)
        self.graveyards[c.orig_owner_id].append(c)
        print(f"{c} has been sent to graveyard from play")
        for a in c.modifiers.auras:
            self.graveyards[c.orig_owner_id].append(a)
            print(f"{a} has been sent to graveyard from play")
        self._send_to_graveyard_or_exile(c)

    def send_to_graveyard(self, c: GameCard):
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
        self.cards_that_died_this_turn.append(c)

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

    def remove_from_any_graveyard(self, c: GameCard) -> GameCard:
        for g in self.graveyards:
            for card in g:
                if card == c:
                    g.remove(c)
                    return c

    def remove_from_your_graveyard(self, c: GameCard, p_idx: int) -> GameCard:
        for card in self.graveyards[p_idx]:
            if card == c:
                self.graveyards[p_idx].remove(c)
                return c

    def add_to_hand(self, c: GameCard, player_idx: int) -> None:
        self.hands[player_idx].cards.append(c)


    # Life Operations; using Registry Pattern
    def increment_life(self, p_id: int, amt: int):
        print(f"Increasing player #{p_id}'s life by {amt}. Life is now at {self.life}")
        self.life[p_id] += amt

    def decrement_life(self, p_id: int, amt: int, source: GameCard):
        """Reduce player life; lookup life loss condition in self.life_loss_registry; check for end game condition"""
        self.life[p_id] -= amt
        print(f"{source.props.name} deals {amt} damage to player #{p_id}. Life is now at {self.life}")

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

    def handle_untap_phase(self):
        """Untap all cards on in-turn player's board; remove summoning sickness"""
        for c in self.boards[self.player_turn_idx].cards:
            for turn_num, act in self.game_history:
                if isinstance(act, CastToBoard) and act.card.id == c.id and self.turn_number - turn_num == 2:
                    c.has_summoning_sickness = False
            if not c.is_tapped:
                continue

            for turn_number, action in self.game_history:
                if (turn_number == self.turn_number and
                        (isinstance(action, UntapCardStackPop) or isinstance(action, LeaveTapped)) and action.source == c):
                    print("You've already made an untap decision on this card this turn")
                    break
            else:
                print(f'Checking on_untap_phase for {c}')
                self.trigger('on_untap_phase', c)
                for a in c.modifiers.auras:
                    if not isinstance(a, GameCard):
                        continue
                    self.trigger('on_untap_phase', a)

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility] = []

        for ability in c.abilities:
            if not ability.can_activate(self):
                continue
            if c.has_summoning_sickness:
                continue

            if ability.eff_spec.target_filter is None:  # janky solution; auras have target_filter = None
                actions.append(ActivateAbility(self.action_on_idx, self, ability, c.attached_to))
                continue

            targets = ability.eff_spec.target_filter(self, c)
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

        def available_actions_from_hand() -> list[Action] | list[None]:
            avail_actions_from_hand: list[Action] = []
            for c in hand.cards:
                if not self.mana_pools[p_id].can_pay(c.casting_cost):
                    continue
                elif c.props.is_land and self.turn.has_played_land:
                    continue
                elif self.player_turn_idx != p_id and 'Instant' not in c.props.card_types:
                    continue
                elif c.props.is_permanent and not c.props.is_aura:
                    avail_actions_from_hand.append(CastToBoard(p_id, self, c))
                else:
                    target_cards: list[GameCard] = c.get_cast_targets(self)
                    # cards that need targets but can't find any, skip ... ex. creature-bond needs a creature
                    if isinstance(target_cards, list) and not target_cards:  # target_cards = []
                        continue
                    # cards that do not require a target
                    if target_cards is None:
                        if 'X' in c.casting_cost:
                            max_x = self.mana_pools[p_id].get_max_x(c.casting_cost)
                            for x in range(max_x + 1):
                                avail_actions_from_hand.append(CastToTargetAddToStack(p_id, self, c, None,
                                                                                      x_values_for_variable_cast=x))
                        else:
                            avail_actions_from_hand.append(CastToTargetAddToStack(p_id, self, c, None))
                        continue
                    # for all possible targets, add as an available action
                    for t in target_cards:
                        if 'X' in c.casting_cost:
                            max_x = self.mana_pools[p_id].get_max_x(c.casting_cost)
                            for x in range(max_x + 1):
                                avail_actions_from_hand.append(CastToTargetAddToStack(p_id, self, c, t,
                                                                                      x_values_for_variable_cast=x))
                        else:
                            avail_actions_from_hand.append(CastToTargetAddToStack(p_id, self, c, t))
            return list({repr(x): x for x in avail_actions_from_hand}.values())  # only return unique (by repr) actions

        # if there is something on the stack, respond & resolve, don't seek out other available actions
        if len(self.action_stack):
            if isinstance(self.action_stack.last_action, ChoiceAction):
                return self.action_stack.last_action.get_actions()

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
            self.handle_untap_phase()
            if len(self.action_stack):
                if isinstance(self.action_stack.last_action, ChoiceAction):
                    return self.action_stack.last_action.get_actions()
            self.phase = Phase.UPKEEP
            return

        if self.phase == Phase.UPKEEP:
            for c in self.boards[self.player_turn_idx].cards:
                self.trigger('upkeep', c)
                if activated_abilities := self.get_available_activated_abilities(c):
                    return [MoveToDrawPhase(c.orig_owner_id, self)] + activated_abilities
            self.phase = Phase.DRAW
            return

        if self.phase == Phase.DRAW:
            return [DrawCard(p_id, self)]

        if self.phase == Phase.CAST:
            available_actions.append(MoveToEndStep(p_id, self))
            available_actions.extend(available_actions_from_hand())
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
            available_actions.append((FinishBlocking(self.action_on_idx, self)))

            remaining_blockers = [c for c in self.boards[self.action_on_idx].available_blockers
                                  if c not in [c for com in self.combats for c in com.blockers]]
            for blocker in remaining_blockers:
                for com in self.combats:
                    if self.can_block(blocker, com.attacker):
                        print(f"[xxx] TRYING TO FIGURE IF {blocker} CAN BLOCK {com.attacker}")
                        available_actions.append(AssignBlocker(self.action_on_idx, self, blocker, com.attacker))

            available_actions.extend(available_actions_from_hand())
            available_actions.extend(add_activated_abilities_from_board())

        if self.phase == Phase.PRE_COMBAT_DAMAGE:
            available_actions.append((AssignCombatDamage(self.action_on_idx, self)))
            available_actions.extend(available_actions_from_hand())
            available_actions.extend(add_activated_abilities_from_board())

        if self.phase == Phase.ASSIGN_COMBAT_DAMAGE:
            self.phase = Phase.FIRST_STRIKE_DAMAGE
            self.phase = Phase.COMBAT_DAMAGE
            for com in self.combats:
                com.handle_damage()
            self.phase = Phase.COMBAT_END
            for b in self.boards:
                for c in b.cards:
                    self.trigger('combat_end', c)
            self.phase = Phase.END_STEP

        if self.phase == Phase.END_STEP:
            # new event emission system
            self.emit(EndStepEvent(active_player=self.player_turn_idx))

            # for all cards on all boards
            for b in self.boards:
                for c in b.cards:
                    self.trigger('end_step', c)
                    for a in c.modifiers.auras:
                        if not isinstance(a, GameCard):  # KWAMods/PTMods are auras but aren't actually GameCards
                            continue
                        self.trigger('end_step', a)

            # execute all end step funcs
            for func in self.end_step_funcs:
                func()

            for c in self.card_filter.in_play().result():
                c.modifiers.clear_temps()
            self.phase = Phase.DISCARD
            return

        if self.phase == Phase.DISCARD:
            for b in self.boards:
                for c in b.cards:
                    self.trigger('discard_step', c)
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
            # Remove all temp global effects
            self.global_effects = [e for e in self.global_effects if not e[2]]
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
                    aa.eff_spec.activated_cnt_this_turn = 0
            # clear combats
            self.combats.clear()
            self.phase = Phase.PASS_THE_TURN
            return

        return available_actions


# TODO:
#  on_leave.py: should there just be a common on_leave so when card leaves, all mods for which it's the source are removed?

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

# TODO:
#  Create a module that queries for game events.
#  - instead of gs.cards_that_died_this_turn, there should be a GameHistoryFilter (like CardFilter)

# TODO:
#  can_cast() must take into account multi-mana-color producers (dual lands, etc)
