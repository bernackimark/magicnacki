import random
from collections import defaultdict
from typing import Callable, Optional, Any

import models.card_attributes.card_effect_specs
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
from models.damage import PreventNextDamage, DamageEvent, DamageReplacement
from models.effects.base import Effect, Triggered
from models.effects.base_rules_queries import CanAttackBaseRule, CanBlockBaseRule
from models.events.base import Event
from models.events.events_all import EndStepEvent, UpkeepEvent, CombatEndEvent, TapCardEvent, UntapCardEvent, \
    UntapPhaseEvent, DamageResolvedEvent, StateBasedEvent, CastResolvedEvent
from models.game_card import GameCard
from models.board import Board
from models.combat import Combat
from models.hand import Hand
from models.mana import ManaPool
from models.state_based_rules import StateBasedRule, IslandhomeSBR
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

        self.query_effects: list[Effect] = [CanAttackBaseRule(), CanBlockBaseRule()]
        self._until_eot: list[Any] = []
        self.state_based_rules: list[type[StateBasedRule]] = [IslandhomeSBR]

        # registries for side effects that are not captured in card effects
        # life-loss registry uses (cond, effect) tuples similar to your TAP_REGISTRY style
        self.life_loss_registry: list[tuple[Callable, Callable]] = [
            # backfire: if the source has an aura with slug 'backfire', deal the same life loss to opponent
            (lambda gs, p_id, amt, source: any(a.props.slug == "backfire" for a in source.modifiers.auras),
             lambda gs, p_id, amt, source: gs._apply_opponent_life_loss(p_id, amt))
        ]

        # default leave handlers: ensure cleanup always occurs even if no slug specific handler
        self.leave_default_handlers: list[Callable] = [lambda gs, c, tgt: c.clear_all_mods()]

        self.damage_replacements: list[DamageReplacement] = []
        self.damage_preventions: list[PreventNextDamage] = []
        self.end_of_turn_effects: list = []
        self.end_step_funcs: list[Callable] = []
        self.cards_that_died_this_turn: list[GameCard] = []

        # --- event registry for new system ---
        # key = Event subclass, value = list of (effect, source_card) tuples
        self._event_listeners: dict[type, list[tuple[Effect, GameCard]]] = defaultdict(list)

    # --- NEW SYSTEM ---
    def register_effect(self, effect: Effect, source_card: GameCard):
        """Store the effect_spec + source card tuple for later event emission."""
        if effect.listens_to:
            self._event_listeners[effect.listens_to].append((effect, source_card))

    def unregister_effects(self, card: GameCard):
        """Remove any event listeners tied to this card."""
        for event_type, effect_list in self._event_listeners.items():
            # Keep only effects whose source_card is not the leaving card
            self._event_listeners[event_type] = [
                (eff, source_card) for eff, source_card in effect_list
                if source_card != card]

    def emit(self, event: Event):
        """Call all effects listening to a certain type of event (ex: EndStepEvent)"""
        for eff, source_card in self._event_listeners[type(event)]:
            eff.resolve(self, source_card, getattr(event, 'target', None))

    def register_until_end_of_turn(self, obj):
        self._until_eot.append(obj)

    def on_query(self, event: str, card: GameCard, **kwargs):
        """Ask all effects whether this event is permitted. If any effect returns False, the action is denied.
        If none return False, action is allowed."""
        # Check local effects on the card
        for eff in card.triggered_abilities:
            if not hasattr(eff, 'on_query'):
                continue
            r = eff.on_query(self, event, card, **kwargs)
            if r is False:
                return False
        return True

    def check_state_based_actions(self):
        """state-based actions must repeat until stable"""
        while True:
            changed = False
            for rule in self.state_based_rules:
                if rule.apply(self):
                    changed = True
            if not changed:
                break

    def can_attack(self, card: GameCard) -> bool:
        """Check base rules. Check card effects & global statics. If any rule returns 'False', the card cannot attack"""
        if card in {com.attacker for com in self.combats}:
            return False

        effects = self.query_effects  # base rules
        effects.extend(card.triggered_abilities)  # card effects
        for c in self.card_filter.in_play().result():  # global statics (ex: moat)
            effects.extend(c.triggered_abilities)
        for eff in effects:
            if not hasattr(eff, 'on_query'):
                continue
            result = eff.on_query(self, 'can_attack', card=card)
            if result is False:
                return False  # hard veto
        return True

    def can_block(self, blocker: GameCard, attacker: GameCard):
        if blocker in {blocker for com in self.combats for blocker in com.blockers}:
            return False

        effects = self.query_effects  # base rules
        effects.extend(attacker.triggered_abilities)  # card effects
        effects.extend(blocker.triggered_abilities)
        for c in self.card_filter.in_play().result():  # global statics (ex: moat)
            effects.extend(c.triggered_abilities)

        for eff in effects:
            if not hasattr(eff, 'on_query'):
                continue
            result = eff.on_query(self, 'can_block', card=blocker, attacker=attacker)
            if result is False:
                return False  # hard veto

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
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int, is_combat: bool = False):
        """Creates DamageEvent, triggers damage preventions, adds .combat_damage_received to card,
        decrements life to player, handles Trample combat damage"""
        event = DamageEvent(source, amount, target, is_combat)

        # 1. Give all effects a chance to prevent/redirect
        self.trigger_damage_prevention(event)

        # 2. Apply remaining damage
        if event.remaining <= 0:
            return

        resolved_events: list[DamageResolvedEvent] = []

        # 3. Apply damage
        if is_combat and source and 'Trample' in source.keyword_abilities and isinstance(target, GameCard):
            damage_to_card = min(target.toughness, event.remaining)
            target.combat_damage_received += damage_to_card
            resolved_events.append(DamageResolvedEvent(source, damage_to_card, target, True))

            damage_to_player = event.remaining - damage_to_card
            if damage_to_player > 0:
                self.decrement_life(target.orig_owner_id, damage_to_player, source)
                resolved_events.append(DamageResolvedEvent(source, damage_to_player, target.orig_owner_id, True))
        else:
            if isinstance(target, GameCard):
                target.combat_damage_received += event.remaining
            else:
                self.decrement_life(target, event.remaining, source)

            resolved_events.append(DamageResolvedEvent(source, event.remaining, target, is_combat))

        # 4. Emit resolved events
        for e in resolved_events:
            self.emit(e)

    def trigger_damage_prevention(self, event: DamageEvent):
        # Replacement effects (statics + globals)
        for r in list(self.damage_replacements):
            if r.applies(self, event):
                r.replace(self, event)

        # One-shot prevention shields (ex: fog, COPs)
        for p in list(self.damage_preventions):
            if event.remaining <= 0:
                break
            prevented = p.apply(event)
            event.prevented += prevented
            if p.remaining == 0:
                self.damage_preventions.remove(p)

    # --- CARD MOVEMENT ---
    def remove_from_board(self, c: GameCard) -> None:
        """Trigger leave event for card (ex Crusade, Castle); remove card from board; remove all auras from board"""
        self.unregister_effects(c)
        self.emit(StateBasedEvent())
        board = self.boards[c.orig_owner_id]
        board.remove_from_board(c)
        print(f"{c} has been removed from the board")
        for a in c.modifiers.auras:
            if isinstance(a, GameCard):
                self.unregister_effects(c)
                board.remove_from_board(a)
                print(f"{a} has been removed from the board")

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
        self.emit(StateBasedEvent())
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

    def tap_card(self, c: GameCard):
        # new system
        if c.is_tapped:
            return
        self.emit(TapCardEvent(card=c))
        # is this all supposed to happen here, in the TapCardEvent(Event), in a dedicated TapCardEffect(Effect)?
        c.is_tapped = True
        for a in c.modifiers.auras:
            models.card_attributes.card_effect_specs.is_tapped = True

    def untap_card(self, c: GameCard):
        # new system
        if not c.is_tapped:
            return
        self.emit(TapCardEvent(card=c))
        # is this all supposed to happen here, in the UntapCardEvent(Event), in a dedicated UntapCardEffect(Effect)?
        c.is_tapped = False
        for a in c.modifiers.auras:
            models.card_attributes.card_effect_specs.is_tapped = False
        self.emit(UntapCardEvent(card=c))

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
                # new system
                self.emit(UntapPhaseEvent(active_player=self.player_turn_idx))
                self.untap_card(c)

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility] = []

        for ability in c.activated_abilities:
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

        self.check_state_based_actions()

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
                if c.props.is_permanent and not c.props.is_aura:
                    avail_actions_from_hand.append(CastToBoard(p_id, self, c))
                    continue

                # --- Get targets ---
                cast_eff_specs = [eff_spec for eff_spec in c.triggered_abilities
                                  if eff_spec.activation_type == 'triggered'
                                  and eff_spec.trigger_event is CastResolvedEvent]

                # if there are no specs or if the target_filter is None, a target is not required & can be played
                if not cast_eff_specs or cast_eff_specs[0].target_filter is None:
                    if 'X' in c.casting_cost:
                        max_x = self.mana_pools[p_id].get_max_x(c.casting_cost)
                        for x in range(max_x + 1):
                            avail_actions_from_hand.append(CastToTargetAddToStack(p_id, self, c, None,
                                                                                  x_values_for_variable_cast=x))
                    else:
                        avail_actions_from_hand.append(CastToTargetAddToStack(p_id, self, c, None))
                    continue

                # Normally there is only one "cast" effect per card; this may become problematic later
                print(f"{cast_eff_specs=}")
                targets: list[GameCard | None] = cast_eff_specs[0].target_filter(self, c)

                # if targets = [], the card needs targets but can't find any, so the card is unplayable
                if isinstance(targets, list) and not targets:
                    continue

                # targets is a list of GameCard; append an available action for each Target
                for t in targets:
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
                # Handle counterspells separately; not thought through yet
                if c.props.slug in ('counterspell',):
                    target: Action = self.action_stack.last_action
                    available_actions.append(CastCounter(p_id, self, c, target))
                    continue

                # Handle other spells
                available_actions.extend(available_actions_from_hand())

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
            self.emit(UpkeepEvent(active_player=self.player_turn_idx))
            for c in self.boards[self.player_turn_idx].cards:
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
            self.emit(CombatEndEvent(active_player=self.player_turn_idx))
            self.phase = Phase.END_STEP

        if self.phase == Phase.END_STEP:
            # new event emission system
            self.emit(EndStepEvent(active_player=self.player_turn_idx))

            # execute all end step funcs
            for func in self.end_step_funcs:
                func()

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
            # new approach
            for obj in self._until_eot:
                if obj in self.damage_preventions:
                    self.damage_preventions.remove(obj)
            self._until_eot.clear()

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
                for aa in c.activated_abilities:
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
