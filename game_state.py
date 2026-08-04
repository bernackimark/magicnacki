from __future__ import annotations
import random
from typing import Any, Sequence, TYPE_CHECKING

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.cast import CastPermanentAction, CastWithNoSpellEffect
from models.effects.base import Activated
from models.systems.priority import PriorityManager
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.card import Card

from models.action_stack import ActionStack
from models.actions.stack_accept_counter import AcceptAction
from models.systems.event import EventManager
from models.actions.base import Action
from models.choice_actions_all import ChoiceAction
from models.systems.combat import CombatManager
from models.events_all import DamageResolvedEvent, RandomEvent, DamageProposedEvent, CostQueryEvent, StateBasedEvent, \
    CanCastQueryEvent
from models.game_card.game_card import GameCard
from models.game_card_filter import CardFilter
from models.game_history import GameHistory
from models.systems.mana import ManaPool
from models.mulligan import MulliganChoice
from models.systems.pile import PileManager
from models.presentation_request import PresentationRequest
from models.systems.permission import PermissionQuerier
from models.systems.score import ScoreManager
from models.systems.turn import TurnManager
from models.systems.phase import PhaseManager

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

        self.combat_mgr = CombatManager(self)
        self.event_mgr = EventManager(self)  # houses, emits, registers, unregisters Listener(Effect)
        self.perm_querier = PermissionQuerier(self)  # convenience for dealing with permission-based queries
        self.phase_mgr = PhaseManager(self)
        self.pile_mgr = PileManager(self)  # handles pile movements (destroy, bounce, etc)
        self.priority_mgr = PriorityManager(self)  # manages action related to the stack
        self.score_mgr = ScoreManager()  # manages life & poison
        self.turn_mgr = TurnManager(self.player_cnt, player_turn_idx)

        self.action_on_idx: int = self.player_turn_idx

        self.mana_pools: list[ManaPool] = [ManaPool(self, i) for i in range(self.player_cnt)]

        self.action_stack = ActionStack()

        self.game_history = GameHistory()  # turn num, p_idx, Action; appended to in engine.play()

        # only has knowledge of the current game; match info is handled in Engine's MatchManager
        self.is_game_over: bool = False
        self.winner: int | None = None

        # used for forced actions that do not go onto the stack (ex: it's resolved that you must discard, select one)
        self.pending_choice: ChoiceAction | None = MulliganChoice(self.player_turn_idx,
                                                                  self, self.rules['mulligan'])
        self._pending_choices: list[ChoiceAction | None] = []

        # objects that carry data to be displayed in UI that aren't common (ex: Show Library)
        self.presentation_requests: list[PresentationRequest] = []

        for i in range(self.player_cnt):
            random.shuffle(self.pile_mgr.libraries[i])
            self.pile_mgr.draw(i, 7, print_output=False)

    @property
    def boards(self) -> list[list[GameCard]]:
        return self.pile_mgr.boards

    @property
    def card_filter(self) -> CardFilter:
        return CardFilter(self)

    @property
    def exiles(self) -> list[list[GameCard]]:
        return self.pile_mgr.exiles

    @property
    def graveyards(self) -> list[list[GameCard]]:
        return self.pile_mgr.graveyards

    @property
    def hands(self) -> list[list[GameCard]]:
        return self.pile_mgr.hands

    @property
    def life(self) -> list[int, int]:
        return self.score_mgr.life
    
    @property
    def player_turn_idx(self) -> int:
        return self.turn_mgr.player_turn_idx

    def queue_choice(self, choice: ChoiceAction):
        if self.pending_choice is None:
            self.pending_choice = choice
        else:
            self._pending_choices.append(choice)

    def add_presentation_request(self, viewer_id: int, type_: str, payload: Any):
        self.presentation_requests.append(PresentationRequest(viewer_id, type_, payload))

    # --- DAMAGE ---
    def apply_damage(self, source: GameCard | None, amount: int, target: GameCard | int, is_combat: bool = False):
        """Creates DamageEvent, triggers damage preventions, adds .combat_damage_received to card,
        decrements life to player, handles Trample combat damage"""
        # 1. Create & emit a DamageProposedEvent, allowing listeners to modify the amount; exit if no remaining damage
        event = DamageProposedEvent(source, target, amount, amount, is_combat=is_combat)
        self.event_mgr.emit(event)
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
            self.event_mgr.emit(e)

        # 5. Check SBAs (ex: damage_received_this_turn >= creature.toughness)
        self.event_mgr.emit(StateBasedEvent())
        # self.check_state_based_actions()

    @staticmethod
    def randomize_event(p_id: int, sequence: Sequence[Any]) -> Any:
        """Creates an event, but doesn't raise it (not sure why not); selects a random choice from the sequence"""
        event = RandomEvent(p_id, sequence)
        event.result = random.choice(sequence)
        return event.result

    # --- CASTING & ACTIVATION COSTS ---
    def get_casting_cost(self, p_id: int, card: GameCard) -> str:
        event = CostQueryEvent(p_id, 'cast', card, card.casting_cost[:] if card.casting_cost else '')
        self.event_mgr.emit(event)
        return event.cost

    def get_activation_cost(self, p_id: int, source: GameCard, ability: Activated) -> str:
        event = CostQueryEvent(p_id, 'activate', source, ability.eff_spec.cost)
        self.event_mgr.emit(event)
        return event.cost

    def get_available_activated_abilities(self, c: GameCard) -> list[AbilityPipeline | None]:
        actions: list[AbilityPipeline | None] = []
        for aa in c.activated_abilities:
            pipeline = AbilityPipeline(c.owner_id, self, c, aa.eff_spec)
            if pipeline.can_begin():
                actions.append(pipeline)
        return actions

    def add_activated_abilities_from_board(self) -> list[AbilityPipeline | None]:
        aas = []
        for c in self.pile_mgr.boards[self.action_on_idx]:
            for a in self.get_available_activated_abilities(c):
                # i'm performing this check here, because I think the caller is gs.action_on_idx
                if a.eff_spec.allowed_activators is not None and self.action_on_idx not in a.eff_spec.allowed_activators(self, c):
                    continue
                aas.append(a)
        for c in self.pile_mgr.boards[flip(self.action_on_idx)]:
            for a in self.get_available_activated_abilities(c):
                if a.eff_spec.allowed_activators and self.action_on_idx in a.eff_spec.allowed_activators(self, c):
                    aas.append(a)
        return aas

    def available_actions_from_hand(self) -> list[AbilityPipeline | CastPermanentAction | CastWithNoSpellEffect | None]:
        """For each card in hand for the in-scope player ...
            -   If not can_cast(), skip (can_cast emits to Listeners, including base game rules)
            -   Lands create CastPermanentAction whose .play() bypasses the stack
            -   Non-land permanents w no spell effect, create a CastWithNoSpellEffect,
                    whose .play() adds a CastPermanentAction to the stack
            -   For each cast effect:
                -   create a AbilityPipeline action (which builds the Ability -- X, mode, target, etc.)
            Return the list of legal Actions"""
        actions: list[AbilityPipeline | CastPermanentAction | CastWithNoSpellEffect | None] = []

        for c in self.pile_mgr.hands[self.action_on_idx]:
            if c.is_land:
                if not self.turn_mgr.has_played_land:
                    # its .play() will bypass the stack
                    actions.append(CastPermanentAction(c.owner_id, self, c))
                    continue

            elif c.props.is_permanent and not c.spells:
                if not self.mana_pools[self.action_on_idx].can_pay(c.casting_cost):
                    continue
                # its .play() will add it to the stack
                query = CanCastQueryEvent(c, self.action_on_idx)
                self.event_mgr.emit(query)
                if query.permission is not False:
                    actions.append(CastWithNoSpellEffect(c.owner_id, self, c))
                continue

            for spell_eff in c.spells:
                # creates a pipeline for selecting: X, mode, targets, extra costs
                pipeline = AbilityPipeline(c.owner_id, self, c, spell_eff)
                if pipeline.can_begin():
                    print('EEE', c)
                    actions.append(pipeline)

        return actions

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

        self.event_mgr.emit(StateBasedEvent())
        # self.check_state_based_actions()

        if self.pending_choice:
            return self.pending_choice.get_actions()

        if self.is_game_over:
            print('The game is over')
            if not self.pending_choice:
                from models.game_over import GameOverChoice
                self.pending_choice = GameOverChoice(p_id, self)
            return self.pending_choice.get_actions()

        # if there is something on the stack, respond & resolve, don't seek out other available actions
        if len(self.action_stack):
            print('ABC123 I have stack !!!')

            if isinstance(self.action_stack.last_action, ChoiceAction):
                return self.action_stack.last_action.get_actions()

            available_actions: list[AbilityPipeline | Action] = [AcceptAction(p_id, self)]
            available_actions.extend(self.add_activated_abilities_from_board())

            # Check instants & sorceries
            hand_instants = [c for c in self.pile_mgr.hands[p_id] if c.is_instant]
            hand_sorceries = [c for c in self.pile_mgr.hands[p_id] if c.is_sorcery]
            allowed_cards = hand_sorceries if p_id == self.player_turn_idx else hand_sorceries + hand_instants
            for a in self.available_actions_from_hand():
                if a.source in allowed_cards:
                    available_actions.append(a)

            return available_actions

        # delegating to phase manager
        return self.phase_mgr.get_actions(p_id)


# TODO:
#  - When deciding which mana to tap, as a strategy, tap colorless mana where possible

# TODO:
#  can_cast() must take into account multi-mana-color producers (dual lands, etc)

# TODO:
#  Mana abilities: Abilities that produce mana do not use the stack and cannot be responded to or countered at all
