from __future__ import annotations
import random
from typing import Any, Sequence, TYPE_CHECKING

from models.effects.base import Activated, ActivatedAbility

if TYPE_CHECKING:
    from models.game_card.card import Card

from models.action_stack import ActionStack
from models.actions.stack_accept_counter import AcceptAction
from models.event_manager import EventManager
from models.actions.activate_ability import ActivateAbility, BeginAbilityActivationAction
from models.actions.base import Action
from models.actions.cast import CastToBoard, CastCounter, BeginSpellCastAction
from models.choice_actions_all import ChoiceAction
from models.combat import CombatManager
from models.events_all import DamageResolvedEvent, RandomEvent, DamageProposedEvent, CostQueryEvent
from models.game_card.game_card import GameCard
from models.game_card_filter import CardFilter
from models.game_history import GameHistory
from models.mana import ManaPool
from models.mulligan import MulliganChoice
from models.pile_manager import PileManager
from models.presentation_request import PresentationRequest
from models.query_manager import PermissionQuerier
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

        self._query_depth = 0  # temp solution

        self.event_mgr = EventManager()  # houses, emits, registers, unregisters Listener(Effect)
        self.phase_mgr = PhaseManager()
        self.pile_mgr = PileManager(self)  # handles pile movements (destroy, bounce, etc)
        self.perm_querier = PermissionQuerier(self)  # convenience for dealing with permission-based queries
        self.score_mgr = ScoreManager()  # manages life & poison
        self.combat_mgr = CombatManager()

        # action, turn, phase (game flow) concepts
        self.turn_mgr = TurnManager(self.player_cnt, player_turn_idx)
        self.action_on_idx: int = self.turn_mgr.player_turn_idx

        self.mana_pools: list[ManaPool] = [ManaPool(self, i) for i in range(self.player_cnt)]

        self.action_stack = ActionStack()

        self.game_history = GameHistory()  # turn num, p_idx, Action; appended to in engine.play()

        self.card_filter = CardFilter(self)
        # only has knowledge of the current game; match info is handled in Engine's MatchManager
        self.is_game_over: bool = False
        self.winner: int | None = None

        self.state_based_rules: tuple[type[StateBasedRule]] = STATE_BASED_RULES

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

    def check_state_based_actions(self):
        """state_based_rules are invariant; they must repeat until stable; there is no player choice, no stack, etc.;
        (ex: creatures w 0 toughness or unattached auras must die, etc.)"""
        for rule in self.state_based_rules:
            rule.apply(self)

    # --- DAMAGE ---
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int, is_combat: bool = False):
        """Creates DamageEvent, triggers damage preventions, adds .combat_damage_received to card,
        decrements life to player, handles Trample combat damage"""
        # 1. Create & emit a DamageProposedEvent, allowing listeners to modify the amount; exit if no remaining damage
        event = DamageProposedEvent(source, target, amount, amount, is_combat=is_combat)
        self.event_mgr.emit(event, self)
        if event.remaining <= 0:
            return

        print('Damage Proposed Event', event)
        # 2. Damage amount is now resolved; handle trample; create DamageResolvedEvent
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

        # 4. Emit resolved events, allowing listeners to react
        for e in resolved_events:
            print('Damage Resolved Event', e)
            self.event_mgr.emit(e, self)

        # 5. Check SBAs (ex: damage_received_this_turn >= creature.toughness)
        self.check_state_based_actions()

    @staticmethod
    def randomize_event(p_id: int, sequence: Sequence[Any]) -> Any:
        """Creates an event, but doesn't raise it (not sure why not); selects a random choice from the sequence"""
        event = RandomEvent(p_id, sequence)
        event.result = random.choice(sequence)
        return event.result

    # --- CASTING & ACTIVATION COSTS ---
    def get_casting_cost(self, p_id: int, card: GameCard) -> str:
        event = CostQueryEvent(p_id, 'cast', card, card.casting_cost[:] if card.casting_cost else '')
        self.event_mgr.emit(event, self)
        return event.cost

    def get_activation_cost(self, p_id: int, source: GameCard, ability: Activated) -> str:
        event = CostQueryEvent(p_id, 'activate', source, ability.eff_spec.cost)
        self.event_mgr.emit(event, self)
        return event.cost

    def get_available_activated_abilities(self, c: GameCard) -> list[ActivateAbility]:
        actions: list[ActivateAbility | BeginAbilityActivationAction] = []

        for eff_spec in c.abilities:
            if eff_spec.activation_type != 'activated':
                continue
            aa = ActivatedAbility(c, eff_spec)
            if not aa.can_activate(self):
                continue

            # Determine potential targets
            target_spec = aa.eff_spec.target_spec

            # If the ability takes no targets, create the ActivateAbility action
            if not target_spec:
                actions.append(ActivateAbility(self.action_on_idx, self, c, eff_spec, target=None))
                continue

            # TODO: THIS IF CHAIN ARE WRONG
            #  EX: mana battery has no target_spec but does have a max_x_func and must enter BeginAbilityActivation ...

            # If the ability requires multiple targets or X needs to be declared, being that flow
            if target_spec.min_cnt > 1 or eff_spec.max_x_func:
                actions.append(BeginAbilityActivationAction(self.action_on_idx, self, c, eff_spec))
                continue

            # For each single legal target, create an ActivateAbility action
            for t in target_spec.get_targets(self, c):
                actions.append(ActivateAbility(self.action_on_idx, self, c, eff_spec, target=t))

        return actions

    def add_activated_abilities_from_board(self) -> list[ActivateAbility] | list[None]:
        return [a for c in self.pile_mgr.boards[self.action_on_idx] for a in self.get_available_activated_abilities(c)]

    def available_actions_from_hand(self) -> list[CastToBoard | BeginSpellCastAction]:
        """For each card in hand for the in-scope player ...
            -   If not can_cast(), skip
            -   If permanent, cast to board directly w/o stack (speed of testing; will need to amend to just lands)
            -   If card has no cast effects, add BeginSpellCastAction as a valid action
            -   For each cast effect:
                -   If X & X can't be paid, skip
                -   If there are no or fewer targets than the effect requires, skip
                -   Else add BeginSpellCastAction as a valid action
            Return list of legal Actions"""
        actions: list[CastToBoard | BeginSpellCastAction] = []
        p_id = self.action_on_idx

        for c in self.pile_mgr.hands[self.action_on_idx].cards:
            if not self.perm_querier.can_cast(c, p_id):
                continue

            # Short-cutting these directly to the board for testing expedience
            if c.props.is_permanent and 'Aura' not in c.card_sub_types:
                actions.append(CastToBoard(p_id, self, c))
                continue

            # Gather abilities tied to casting
            spell_effect_specs = [e for e in c.abilities if e.activation_type == 'spell']

            if not spell_effect_specs:
                actions.append(BeginSpellCastAction(p_id, self, c, eff_spec=None))
                continue

            # --- For each spell effect spec ---
            for spell_eff in spell_effect_specs:
                if 'X' in c.casting_cost and self.mana_pools[p_id].get_max_x(c.casting_cost) < spell_eff.min_x:
                    continue

                if spell_eff.target_spec and spell_eff.target_spec.filter_func:
                    candidates = spell_eff.target_spec.filter_func(self, c)
                    valid_targets = [t for t in candidates if self.perm_querier.can_target(t, c)]
                    if len(valid_targets) < spell_eff.target_spec.min_cnt:
                        continue

                actions.append(BeginSpellCastAction(p_id, self, c, eff_spec=spell_eff))

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
