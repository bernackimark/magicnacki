from __future__ import annotations
import random
from typing import Callable, Any, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.card import Card

from models.action_stack import ActionStack
from models.actions.stack_accept_counter import AcceptAction
from models.event_manager import EventManager
from models.actions.activate_ability import ActivateAbility, BeginAbilityActivationAction
from models.actions.base import Action
from models.actions.cast import CastToBoard, CastCounter, BeginSpellCastAction
from models.choice_actions_all import ChoiceAction
from models.combat import Combat
from models.damage import PreventNextDamage
from models.destroy_replacements import RegenerationShield
from models.effects.base import Effect
from models.events_all import TapCardEvent, UntapCardEvent, DamageResolvedEvent, CastResolvedEvent, RandomEvent, \
    DamageProposedEvent
from models.game_card.game_card import GameCard
from models.game_card_filter import CardFilter
from models.game_history import GameHistory
from models.mana import ManaPool
from models.mulligan import MulliganChoice
from models.pile_manager import PileManager
from models.presentation_request import PresentationRequest
from models.query_manager import QueryManager
from models.score_manager import ScoreManager
from models.state_based_rules import StateBasedRule, STATE_BASED_RULES
from models.turn_manager import TurnManager
from models.phase_manager import PhaseManager

class GameState:
    """All-knowing class responsible for everything after a new game is created;
    delegates like logic to helper classes (PhaseManager, PileManager, etc.);
    contains stack & pending choice; gets available actions"""
    def __init__(self, player_cnt: int, player_turn_idx: int, rules: dict, cards: list[list[GameCard]],
                 tokens: dict[str, Card]):
        # assign all arguments to attributes
        self.player_cnt = player_cnt
        self.rules: dict = rules
        self.tokens = tokens
        self.all_player_cards = cards.copy()

        self.event_mgr = EventManager()  # houses, emits, registers, unregisters Listener(Effect)
        self.phase_mgr = PhaseManager()
        self.pile_mgr = PileManager(self)  # handles pile movements (destroy, bounce, etc)
        self.query_mgr = QueryManager(self)  # handles effects that are Querier(Effect)
        self.score_mgr = ScoreManager()  # manages life & poison

        # action, turn, phase (game flow) concepts; not sure self.turn is being used
        self.turn_mgr = TurnManager(self.player_cnt, player_turn_idx)
        self.action_on_idx: int = self.turn_mgr.player_turn_idx

        self.combats: list[Combat] = []
        self.mana_pools: list[ManaPool] = [ManaPool(self, i) for i in range(self.player_cnt)]

        self.action_stack = ActionStack()

        self.game_history = GameHistory()  # turn num, p_idx, Action; appended to in engine.play()

        self.card_filter = CardFilter(self)
        # only has knowledge of the current game; match info is handled in Engine's MatchManager
        self.is_game_over: bool = False
        self.winner: int | None = None

        self.until_eot_effects_and_cards: list[tuple[Effect, GameCard]] = []
        self.state_based_rules: tuple[type[StateBasedRule]] = STATE_BASED_RULES

        self.destroy_replacements: list[RegenerationShield] = []
        self.damage_preventions: list[PreventNextDamage] = []
        self.end_step_funcs: list[Callable] = []
        self.cards_that_died_this_turn: list[GameCard] = []

        # used for forced actions that do not go onto the stack (ex: it's resolved that you must discard, select one)
        self.pending_choice: ChoiceAction | None = MulliganChoice(self.turn_mgr.player_turn_idx,
                                                                  self, self.rules['mulligan'])

        # objects that carry data to be displayed in UI that aren't common (ex: Show Library)
        self.presentation_requests: list[PresentationRequest] = []

        for i in range(self.player_cnt):
            random.shuffle(self.pile_mgr.libraries[i])
            self.pile_mgr.draw(i, 7)

    def add_presentation_request(self, viewer_id: int, type_: str, payload: Any):
        self.presentation_requests.append(PresentationRequest(viewer_id, type_, payload))

    def register_effect_until_eot(self, eff_and_card: tuple[Effect, GameCard]):
        """When GameCards look if they are effected by something, they check the cards in play;
        however, some card effects (such as instants cast & placed in graveyard) last throughout the turn"""
        self.until_eot_effects_and_cards.append(eff_and_card)

    def check_state_based_actions(self):
        """state_based_rules are invariant; they must repeat until stable; there is no player choice, no stack, etc.;
        (ex: creatures w 0 toughness or unattached auras must die, etc.)"""
        for rule in self.state_based_rules:
            rule.apply(self)

    # Pile Helpers & card movement
    @property
    def all_cards(self) -> list[GameCard]:
        """Returns all cards, including tokens"""
        return ([c for lib in self.pile_mgr.libraries for c in lib] + [c for h in self.pile_mgr.hands for c in h.cards] +
                [c for g in self.pile_mgr.graveyards for c in g] + [c for e in self.pile_mgr.exiles for c in e] +
                [c for b in self.pile_mgr.boards for c in b])

    # --- DAMAGE ---
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int, is_combat: bool = False):
        """Creates DamageEvent, triggers damage preventions, adds .combat_damage_received to card,
        decrements life to player, handles Trample combat damage"""
        # event = DamageEvent(source, amount, target, is_combat)  # now replaced w the DamageProposedEvent approach
        event = DamageProposedEvent(source, target, amount, is_combat)
        self.event_mgr.emit(event, self)

        for eff, source_card in self.until_eot_effects_and_cards:
            if hasattr(eff, 'on_event'):
                eff.on_event(self, source_card, event)

        # TODO: the new approach is creating DamageProposedEvent Listeners, but some are stored in until_eot_effects,
        #  which is not be iterated over ...
        #  must iterate and then determine if they should be removed as in self.trigger_damage_prevention()

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
                self.score_mgr.decrement_life(target.owner_id, damage_to_player, source, self)
                resolved_events.append(DamageResolvedEvent(source, damage_to_player, target.owner_id, True))
        else:
            if isinstance(target, GameCard):
                target.damage_received_this_turn += event.remaining
            else:
                self.score_mgr.decrement_life(target, event.remaining, source, self)

            resolved_events.append(DamageResolvedEvent(source, event.remaining, target, is_combat))

        # 4. Emit resolved events
        for e in resolved_events:
            self.event_mgr.emit(e, self)

        # 5. Check SBAs
        self.check_state_based_actions()  # checks if damage_received_this_turn >= creature.toughness

    @staticmethod
    def randomize_event(p_id: int, sequence: Sequence[Any]) -> Any:
        """Creates an event, but doesn't raise it (not sure why not); selects a random choice from the sequence"""
        event = RandomEvent(p_id, sequence)
        event.result = random.choice(sequence)
        return event.result

    def remove_from_combat(self, c: GameCard):
        """If attacker, delete that combat object, untap attacker; if blocker, remove blocker from the combat object"""
        for com in self.combats:
            if com.attacker is c:
                self.untap_card(com.attacker)
                self.combats.remove(com)
                return
            for blocker in com.blockers:
                if blocker is c:
                    com.blockers.remove(blocker)
                    return

    def tap_card(self, c: GameCard):
        """If card is already tapped, skip; emit TapCardEvent & tap card"""
        if c.is_tapped:
            return
        self.event_mgr.emit(TapCardEvent(card=c), self)
        c.is_tapped = True

    def untap_card(self, c: GameCard):
        """If card is already untapped, skip; emit UntapCardEvent & untap card"""
        if not c.is_tapped:
            return
        self.event_mgr.emit(UntapCardEvent(card=c), self)
        c.is_tapped = False

    def handle_untap_phase(self):
        """Untap all cards on in-turn player's board; remove summoning sickness;
        if a card has an optional untap, check if player has already decided to leave a card tapped"""
        for c in self.pile_mgr.boards[self.turn_mgr.player_turn_idx]:
            if not c.is_tapped:
                continue

            for record in self.game_history.items:
                if (record['turn_num'] == self.turn_mgr.turn_number and
                        (record.get('type') == 'UntapCardStackPop' or record.get('type') == 'LeaveTapped')
                        and record.get('card_id') == c.id_):
                    print("You've already made an untap decision on this card this turn")
                    break
            else:
                if self.query_mgr.can_untap(c):
                    self.event_mgr.emit(UntapCardEvent(c), self)
                    self.untap_card(c)

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility | BeginAbilityActivationAction] = []

        for ability in c.activated_abilities:
            spec = ability.eff_spec

            if not ability.can_activate(self):
                continue
            if spec.extra_costs and any(not cost.can_pay(self, c) for cost in spec.extra_costs):
                continue
            if c.has_summoning_sickness:
                continue

            # Determine potential targets
            target_spec = ability.eff_spec.target_spec

            # TODO: THIS IF CHAIN ARE WRONG
            #  EX: mana battery has no target_spec but does have a max_x_func and must enter BeginAbilityActivation ...

            if (target_spec and target_spec.min_cnt > 1) or ability.eff_spec.max_x_func:
                actions.append(BeginAbilityActivationAction(self.action_on_idx, self, ability))
                continue

            if not target_spec:
                actions.append(ActivateAbility(self.action_on_idx, self, ability, target=None))
                continue

            targets = target_spec.filter_func(self, c)
            # convert to list
            targets = [targets] if not isinstance(targets, (list, tuple)) else targets
            # remove illegal targets
            if isinstance(targets[0], GameCard):
                targets = [t for t in targets
                           if self.query_mgr.can_target(t, c, t.host if isinstance(t, GameCard) else None)]
            if len(targets) < target_spec.min_cnt:
                # Not enough legal targets → skip ability entirely
                continue

            actions.append(ActivateAbility(self.action_on_idx, self, ability, target=targets))

        return actions

    def add_activated_abilities_from_board(self) -> list[ActivateAbility] | list[None]:
        actions: list[ActivateAbility] = []
        for card in self.pile_mgr.boards[self.action_on_idx]:
            actions.extend(self.get_available_activated_abilities(card))

        return actions

    def available_actions_from_hand(self) -> list[Action]:
        """For each card in hand for the in-scope player ...
            -   If not can_cast(), skip
            -   If permanent, cast to board directly w/o stack (speed of testing; will need to amend to just lands)
            -   If card has no cast effects, add BeginSpellCastAction as a valid action
            -   For each cast effect:
                -   If X & X can't be paid, skip
                -   If there are no or fewer targets than the effect requires, skip
                -   Else add BeginSpellCastAction as a valid action
            Return list of legal Actions"""
        actions: list[Action] = []
        p_id = self.action_on_idx

        for c in self.pile_mgr.hands[self.action_on_idx].cards:
            if not self.query_mgr.can_cast(c, p_id):
                continue

            # Short-cutting these directly to the board for testing expedience
            if c.props.is_permanent:
                actions.append(CastToBoard(p_id, self, c))
                continue

            # Gather triggered abilities tied to casting
            cast_eff_specs = [e for e in c.triggered_abilities
                              if e.activation_type == 'triggered' and e.trigger_event is CastResolvedEvent]

            if not cast_eff_specs:
                actions.append(BeginSpellCastAction(p_id, self, c, eff_spec=None))
                continue

            # --- For each cast-triggered spec
            for eff_spec in cast_eff_specs:
                if 'X' in c.casting_cost and self.mana_pools[p_id].get_max_x(c.casting_cost) < eff_spec.min_x:
                    continue

                if eff_spec.target_spec and eff_spec.target_spec.filter_func:
                    candidates = eff_spec.target_spec.filter_func(self, c)
                    valid_targets = [t for t in candidates if
                                     self.query_mgr.can_target(t, c, t.host if isinstance(t, GameCard) else None)]

                    if len(valid_targets) < eff_spec.target_spec.min_cnt:
                        continue

                actions.append(BeginSpellCastAction(p_id, self, c, eff_spec=eff_spec))

        return list({repr(x): x for x in actions}.values())  # Deduplicate by repr

    def get_available_actions(self, p_id: int) -> list[Action] | None:
        """This method is called by the engine; in order, check for:
            -   Pending Choice (selections that are forced & are not placed on stack)
            -   Check global state-based actions (game over, creatures w 0 weakness die, etc.)
                -   If game is over, ask player to sideboard
            -   Pending Choice again, since state-based actions may produce a choice
            -   Check the stack
            -   Get actions by phase"""

        if self.pending_choice:
            return self.pending_choice.get_actions()

        self.check_state_based_actions()

        if self.pending_choice:
            return self.pending_choice.get_actions()

        if self.is_game_over:
            print('YYY')
            if not self.pending_choice:
                from models.game_over import GameOverChoice
                self.pending_choice = GameOverChoice(p_id, self)
            return self.pending_choice.get_actions()

        # if there is something on the stack, respond & resolve, don't seek out other available actions
        if len(self.action_stack):
            available_actions: list[Action] = []
            hand = self.pile_mgr.hands[p_id]
            if isinstance(self.action_stack.last_action, ChoiceAction):
                return self.action_stack.last_action.get_actions()

            available_actions.append(AcceptAction(p_id, self))

            # Check instants (or other spells allowed to respond)
            allowed_cards = hand.instants + hand.sorceries if p_id == self.turn_mgr.player_turn_idx else hand.sorceries
            playable_cards: list[GameCard] = [c for c in allowed_cards if self.mana_pools[p_id].can_pay(c.casting_cost)]

            for c in playable_cards:
                # Handle counterspells separately; not thought through yet
                if c.props.slug in ('counterspell',):
                    target: Action = self.action_stack.last_action
                    available_actions.append(CastCounter(p_id, self, c, target))
                    continue

                # Handle other spells
                available_actions.extend(self.available_actions_from_hand())

                # Activated abilities can also respond
                available_actions.extend(self.add_activated_abilities_from_board())

            return available_actions

        # delegating to phase manager
        return self.phase_mgr.get_actions(p_id, self)


# TODO:
#  - When deciding which mana to tap, as a strategy, tap colorless mana where possible

# TODO:
#  can_cast() must take into account multi-mana-color producers (dual lands, etc)

# TODO: proper stack resolution (according to ChatGPT)
#
#   while True:
#     player = self.current_priority_player()
#
#     action = player.choose_action()
#
#     if action:
#         self.action_stack.push(action)
#         continue
#
#     self.mark_player_passed(player)
#
#     if both_players_passed():
#         resolve_top_of_stack()
#         reset_passes()
# Without this, regeneration can never be used correctly.
