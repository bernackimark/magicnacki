import random
from collections import defaultdict
from typing import Callable

from action_stack import ActionStack
from deck_builder.build_deck import Deck
from card_filter import CardFilter
from models.actions.activate_ability import ActivateAbility
from models.actions.base import Action
from models.actions.cast import CastToBoard, CastToTargetAddToStack, CastCounter
from models.choice_actions.base import ChoiceAction
from models.actions.tap_untap import UntapCardStackPop, LeaveTapped
from models.actions.combat import (CreatureAttack, BeginCombat, FinishDeclaringAttackers, AssignBlocker,
                                   FinishBlocking, AssignCombatDamage)
from models.actions.draw_discard import DrawCard, DiscardCard, MoveToDrawPhase
from models.actions.end_step_pass_turn import MoveToEndStep, PassTheTurn
from models.actions.stack_accept_counter import AcceptAction
from models.damage import PreventNextDamage, DamageEvent, DamageReplacement
from models.effects.base import Effect
from models.effects.base_rules_queries import CanAttackBaseRule, CanBlockBaseRule, CanCastBaseRule
from models.events.base import Event
from models.events.events_all import EndStepEvent, UpkeepEvent, CombatEndEvent, TapCardEvent, UntapCardEvent, \
    UntapPhaseEvent, DamageResolvedEvent, StateBasedEvent, CastResolvedEvent, DiesEvent, ZoneChangeEvent, DrawCardEvent, \
    DrawStepEvent
from models.game_card import GameCard
from models.combat import Combat
from models.hand import Hand
from models.mana import ManaPool
from models.state_based_rules import StateBasedRule, IslandhomeSBR
from models.turn import Turn
from models.zone import Zone
from phase_fsm import Phase
from utils import flip


class GameState:
    def __init__(self, player_cnt: int, player_turn_idx: int, decks: list[Deck]):
        self.player_cnt = player_cnt
        self.player_turn_idx = player_turn_idx
        self._decks = decks  # the decks should not be mutated from inside GameState
        self.libraries = decks.copy()
        for d in self.libraries:
            for c in d.cards:
                c.game_state = self
        self.decks_all_cards = decks.copy()
        self.life = [20, 20]
        self._poison_counters = [0, 0]
        self.action_on_idx: int = self.player_turn_idx
        self.turn = Turn(self.player_turn_idx, flip(self.player_turn_idx))
        self.boards: list[list[GameCard]] = [[] for _ in range(self.player_cnt)]
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

        self.query_effects: list[Effect] = [CanAttackBaseRule(), CanBlockBaseRule(), CanCastBaseRule()]
        self.until_eot_effects_and_cards: list[tuple[Effect, GameCard]] = []
        self.state_based_rules: list[type[StateBasedRule]] = [IslandhomeSBR]

        self.damage_replacements: list[DamageReplacement] = []
        self.damage_preventions: list[PreventNextDamage] = []
        self.end_step_funcs: list[Callable] = []
        self.cards_that_died_this_turn: list[GameCard] = []

        # --- event registry for new system ---
        # key = Event subclass, value = list of (effect, source_card) tuples
        self._event_listeners: dict[type, list[tuple[Effect, GameCard]]] = defaultdict(list)

        for i in range(self.player_cnt):
            random.shuffle(self.libraries[i].cards)
            self.draw(i, 7)

    # --- EVENT LISTENER SYSTEM ---
    def emit(self, event: Event):
        """Call all effects listening to a certain type of event (ex: EndStepEvent); only Effects w 'on_event' listen"""
        for eff, source_card in self._event_listeners[type(event)]:
            if hasattr(eff, 'on_event'):
                eff.on_event(self, source_card, event)

    def register_effect(self, effect: Effect, source_card: GameCard):
        """Store the effect + source card tuple for later event emission."""
        if effect and effect.listens_to:
            self._event_listeners[effect.listens_to].append((effect, source_card))

    def unregister_effects(self, card: GameCard):
        """Remove any event listeners tied to this card."""
        for event_type, effect_list in self._event_listeners.items():
            # Keep only effects whose source_card is not the leaving card
            self._event_listeners[event_type] = [
                (eff, source_card) for eff, source_card in effect_list
                if source_card != card]

    def register_effect_until_eot(self, eff_and_card: tuple[Effect, GameCard]):
        """When GameCards look if they are effected by something,they check the cards in play; however,
        some card effects (such as instants that are cast and go to the graveyard) last throughout the turn"""
        self.until_eot_effects_and_cards.append(eff_and_card)

    def check_state_based_actions(self):
        """state_based_rules are invariant; they must repeat until stable; there is no player choice, no stack, etc.;
        (ex: creatures w 0 toughness or unattached auras must die, etc.)"""
        while True:
            changed = False
            for rule in self.state_based_rules:
                if rule.apply(self):
                    changed = True
            if not changed:
                break

    # --- QUERY SYSTEM ---
    def can_attack(self, card: GameCard) -> bool:
        return self._query_effects_by_event('can_attack', card)

    def can_block(self, blocker: GameCard, attacker: GameCard):
        return self._query_effects_by_event('can_block', blocker, attacker=attacker)

    def can_untap(self, card: GameCard) -> bool:
        return self._query_effects_by_event('can_untap', card)

    def can_cast(self, card: GameCard, p_id: int) -> bool:
        return self._query_effects_by_event('can_cast', card, p_id=p_id)

    def _query_effects_by_event(self, event_str: str, card: GameCard, **kwargs) -> bool:
        """Ask all query-style effects (base, card, and until_eots) if they have an opinion;
        can be True (which is either hard permission or the lack of a hard-veto) or False (a hard veto);
        hard permission takes precedence over hard veto;
        hard permission ex: undertow & islandwalkers can be blocked;
        hard veto ex: meekstone preventing some untaps"""
        effects = (self.query_effects +
                   [a.effect for c in self.card_filter.in_play().result()
                    for a in c.static_abilities + c.triggered_abilities] +
                   [eff for eff, _ in self.until_eot_effects_and_cards])

        explicit_forbids = False
        for eff in effects:
            if not hasattr(eff, 'on_query'):
                continue

            result = eff.on_query(self, event_str, card=card, **kwargs)

            if result is True:
                return True
            if result is False:
                explicit_forbids = True
        return False if explicit_forbids else True

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
        return ([c for b in self.libraries for c in b.cards] + [c for h in self.hands for c in h.cards] +
                [c for g in self.graveyards for c in g] + [c for e in self.exiles for c in e] +
                [c for b in self.boards for c in b])

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
            target.damage_received_this_turn += damage_to_card
            resolved_events.append(DamageResolvedEvent(source, damage_to_card, target, True))

            damage_to_player = event.remaining - damage_to_card
            if damage_to_player > 0:
                self.decrement_life(target.orig_owner_id, damage_to_player, source)
                resolved_events.append(DamageResolvedEvent(source, damage_to_player, target.orig_owner_id, True))
        else:
            if isinstance(target, GameCard):
                target.damage_received_this_turn += event.remaining
                if target.damage_received_this_turn >= target.toughness:  # this doesn't feel correct here
                    self.destroy(target)
            else:
                self.decrement_life(target, event.remaining, source)

            resolved_events.append(DamageResolvedEvent(source, event.remaining, target, is_combat))

        # 4. Emit resolved events
        for e in resolved_events:
            self.emit(e)
            # TODO: i don't think anything is listening for these events

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
    def move_card(self, card: GameCard, to_zone: Zone, *, cause: str | None = None, emit_zone_event: bool = True):
        if card.zone == to_zone:
            return

        # Unregister effects, remove all mods if leaving battlefield
        if card.zone == Zone.BATTLEFIELD:
            self._leave_battlefield(card, to_zone)

        self._remove_from_zone(card, card.zone)
        self._add_to_zone(card, to_zone)
        self._set_zone(card, to_zone)
        if emit_zone_event:
            self.emit(ZoneChangeEvent(card, card.zone, to_zone, cause))

        # Post-move hooks
        # self._after_zone_change(card, from_zone, to_zone)

    def destroy(self, card: GameCard):
        self.move_card(card, Zone.GRAVEYARD, cause="destroy")
        self.cards_that_died_this_turn.append(card)
        self.emit(DiesEvent(card))
        print(f'{card} is destroyed')

    def exile(self, card: GameCard):
        self.move_card(card, Zone.EXILE, cause="exile")
        print(f'{card} is exiled')

    def bounce(self, card: GameCard):
        self.move_card(card, Zone.HAND, cause="bounce")
        print(f'{card} is bounced')

    def discard(self, card: GameCard):
        self.move_card(card, Zone.GRAVEYARD, cause="discard")
        print(f'{card} is discarded')

    def reanimate(self, card: GameCard):
        self.move_card(card, Zone.BATTLEFIELD, cause='reanimate')
        print(f'{card} is reanimated')

    def cast(self, card: GameCard):
        self.move_card(card, Zone.BATTLEFIELD, cause='cast')

    def draw(self, p_id: int, cnt: int = 1):
        for _ in range(cnt):
            self.move_card(self.libraries[p_id].cards[0], Zone.HAND, cause='draw')
            self.emit(DrawCardEvent(p_id))
            print(f'Player #{p_id} draws')

    def _add_to_zone(self, card: GameCard, zone: Zone):
        match zone:
            case Zone.BATTLEFIELD:
                self.boards[card.owner_id].append(card)
            case Zone.HAND:
                self.hands[card.orig_owner_id].cards.append(card)
                self.hands[card.orig_owner_id].sort_cards()
            case Zone.GRAVEYARD:
                self.graveyards[card.orig_owner_id].append(card)
                print(f'added {card} to graveyard here')
            case Zone.EXILE:
                self.exiles[card.orig_owner_id].append(card)
            case Zone.LIBRARY:
                self.libraries[card.orig_owner_id].cards.append(card)  # should this place the card at 0th position?

    def _remove_from_zone(self, card: GameCard, zone: Zone):
        match zone:
            case Zone.BATTLEFIELD:
                self.boards[card.owner_id].remove(card)
            case Zone.HAND:
                self.hands[card.owner_id].cards.remove(card)
                self.hands[card.orig_owner_id].sort_cards()
            case Zone.GRAVEYARD:
                self.graveyards[card.owner_id].remove(card)
            case Zone.EXILE:
                self.exiles[card.owner_id].remove(card)
            case Zone.LIBRARY:
                self.libraries[card.owner_id].cards.remove(card)

    @staticmethod
    def _set_zone(card: GameCard, zone: Zone):
        card.zone = zone

    def _leave_battlefield(self, card: GameCard, to_zone: Zone):
        """Emit ZoneChangeEvent before unregistering its effects"""
        self.emit(ZoneChangeEvent(card, card.zone, to_zone, cause='leave'))
        self.unregister_effects(card)
        for aura in list(card.modifiers.auras):
            if isinstance(aura, GameCard):
                self.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'))
                self.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
                self.unregister_effects(aura)
        card.clear_all_mods()
        self.emit(StateBasedEvent())

    # THIS IS A RELATED CONCEPT THAT DOESN'T BELONG HERE.  JUST STORING HERE TEMPORARILY
    # class DiesTrigger(TriggeredAbility):
    #     def matches(self, event):
    #         return isinstance(event, ZoneChangeEvent) and event.from_zone == Zone.BATTLEFIELD
    #           and event.to_zone == Zone.GRAVEYARD

    # Life Operations; using Registry Pattern
    def increment_life(self, p_id: int, amt: int):
        print(f"Increasing player #{p_id}'s life by {amt}. Life is now at {self.life}")
        self.life[p_id] += amt

    def decrement_life(self, p_id: int, amt: int, source: GameCard):
        """Reduce player life; check for end game condition"""
        self.life[p_id] -= amt
        print(f"{source.props.name} deals {amt} damage to player #{p_id}. Life is now at {self.life}")

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
        c.is_tapped = True
        for a in c.modifiers.auras:
            a.is_tapped = True

    def untap_card(self, c: GameCard):
        # new system
        if not c.is_tapped:
            return
        self.emit(UntapCardEvent(card=c))
        # is this all supposed to happen here, in the UntapCardEvent(Event), in a dedicated UntapCardEffect(Effect)?
        c.is_tapped = False
        for a in c.modifiers.auras:
            a.is_tapped = False

    def handle_untap_phase(self):
        """Untap all cards on in-turn player's board; remove summoning sickness;
        if a card has an optional untap, check if player has already decided to leave a card tapped"""
        for c in self.boards[self.player_turn_idx]:
            for turn_num, act in self.game_history:
                if isinstance(act, CastToBoard) and act.card is c and self.turn_number - turn_num == 2:
                    c.has_summoning_sickness = False
            if not c.is_tapped:
                continue

            for turn_number, action in self.game_history:
                if (turn_number == self.turn_number and
                        (isinstance(action, UntapCardStackPop) or
                         isinstance(action, LeaveTapped)) and action.card == c):
                    print("You've already made an untap decision on this card this turn")
                    break
            else:
                if self.can_untap(c):
                    self.emit(UntapPhaseEvent(active_player=self.player_turn_idx))
                    self.untap_card(c)

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility] = []

        for ability in c.activated_abilities:
            if not ability.can_activate(self):
                continue
            if ability.eff_spec.extra_costs:
                for extra_cost in ability.eff_spec.extra_costs:
                    if not extra_cost.can_pay(self, c):
                        continue  # this just break out of this loop, or does it exit entire ability loop (desired)?
            if c.has_summoning_sickness:
                continue

            if ability.eff_spec.target_filter is None and c.attached_to:  # janky solution
                actions.append(ActivateAbility(self.action_on_idx, self, ability, c.attached_to))
                continue

            targets = ability.eff_spec.target_filter(self, c) if ability.eff_spec.target_filter else None
            # Returns None | GameCard | list[GameCard] | tuple[int] (targets p_id's) | int (targets a single p_id)
            print(f"{c=}, {ability=}, {targets=}")

            # I need at least one target, but I don't have any.  Skip.
            if isinstance(targets, (list, tuple)) and not len(targets):
                continue

            # convert targets into something iterable
            targets = [targets] if not isinstance(targets, (list, tuple)) else targets

            for t in targets:
                if 'X' in ability.eff_spec.cost:
                    min_x = ability.eff_spec.min_x
                    max_x = ability.eff_spec.max_variable_x_func(self, c)
                    for x in range(min_x, max_x + 1):
                        actions.append(ActivateAbility(self.action_on_idx, self, ability, t, x))
                else:
                    actions.append(ActivateAbility(self.action_on_idx, self, ability, t))

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
            for card in board:
                actions.extend(self.get_available_activated_abilities(card))
                for aura in card.modifiers.auras:
                    if not isinstance(aura, GameCard):  # some auras can be KWAModifier/PTModifiers (this is confusing)
                        continue
                    actions.extend(self.get_available_activated_abilities(aura))
            return actions

        def available_actions_from_hand() -> list[Action] | list[None]:
            avail_actions_from_hand: list[Action] = []
            for c in hand.cards:
                if self.can_cast(c, p_id) is False:
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

                # targets is a list of GameCard; append available action for each Target & each target-variable_X combo
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
            for c in self.boards[self.player_turn_idx]:
                if activated_abilities := self.get_available_activated_abilities(c):
                    return [MoveToDrawPhase(c.orig_owner_id, self)] + activated_abilities
            self.phase = Phase.DRAW
            return

        if self.phase == Phase.DRAW:
            self.emit(DrawStepEvent(active_player=self.player_turn_idx))
            return [DrawCard(p_id, self)]

        if self.phase == Phase.CAST:
            available_actions.append(MoveToEndStep(p_id, self))
            available_actions.extend(available_actions_from_hand())
            available_actions.extend(add_activated_abilities_from_board())

            # declare combat
            if any(self.can_attack(card) for card in board):
                available_actions.append(BeginCombat(p_id, self))

        if self.phase == Phase.DECLARE_ATTACKERS:
            if self.combats:
                available_actions.append(FinishDeclaringAttackers(p_id, self))

            for c in board:
                if self.can_attack(c):
                    available_actions.append(CreatureAttack(p_id, self, c))

        if self.phase == Phase.DECLARE_BLOCKERS:
            available_actions.append((FinishBlocking(self.action_on_idx, self)))

            for blocker in self.card_filter.on_player_board(self.action_on_idx).creatures().result():
                for com in self.combats:
                    if self.can_block(blocker, com.attacker):
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
            # THIS NEEDS A RE-WRITE:
            # 1) I don't want to use decks_all_cards
            # 2) doesn't feel the right way to expire expiring damage
            for deck in self.decks_all_cards:
                for c in deck.cards:
                    c.damage_dealt_this_turn = 0
                    c.damage_received_this_turn = 0
            self.phase = Phase.END_TURN_EFFECTS

        if self.phase == Phase.END_TURN_EFFECTS:
            # new approach
            for eff, card in self.until_eot_effects_and_cards:
                if eff in self.damage_preventions:
                    self.until_eot_effects_and_cards = [i for i in self.until_eot_effects_and_cards if i != eff]
            self.until_eot_effects_and_cards.clear()

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
#  - When deciding which mana to tap, as a strategy, tap colorless mana where possible

# TODO:
#  Build a CardUniverseFilter (modeled after CardFilter)
#  - helpful when I'm trying to figure out what are good cards to test
#  - would be helpful to the User when Building a Deck

# TODO:
#  can_cast() must take into account multi-mana-color producers (dual lands, etc)
