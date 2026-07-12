from __future__ import annotations
from abc import ABC
from enum import auto, IntEnum
from typing import TYPE_CHECKING

from models.events_all import UntapCardEvent, CanEnterUntapPhaseQueryEvent

if TYPE_CHECKING:
    from models.actions.base import Action
    from game_state import GameState

from models.utils import flip

class Phase(IntEnum):
    NEW_SESSION = auto()  # roll dice; decide going first
    NEW_GAME = auto()  # shuffle; deal; mulligan
    SIDEBOARDING = auto()
    UNTAP = auto()  # (phasing happens, if relevant); untap permanents
    UPKEEP = auto()  # any player can cast instants & activate abilities (CIAA)
    DRAW = auto()  # draw a card; any player can CIAA
    MAIN = auto()  # cast sorceries & perms; CIAA
    DECLARE_COMBAT = auto()  # CIAA
    DECLARE_ATTACKERS = auto()  # declare who is attacking; tap those w/o vigil
    DECLARE_BLOCKERS = auto()  # declare who's blocking whom
    PRE_COMBAT_DAMAGE = auto()  # CIAA
    ASSIGN_COMBAT_DAMAGE = auto()
    FIRST_STRIKE_DAMAGE = auto()  # 1st/double strike assigned; CIAA
    COMBAT_DAMAGE = auto()  # non-1st/double strike deal combat damage; CIAA
    COMBAT_END = auto()  # CIAA
    SECOND_MAIN = auto()
    END_STEP = auto()  # CIAA
    DISCARD = auto()  # CIAA
    CREATURES_HEAL = auto()  # remove damage from perms
    END_TURN_EFFECTS = auto()  # end 'this turn' & 'til end of turn' effects
    PASS_THE_TURN = auto()  # resolve end of turn effects


class PhaseState(ABC):
    phase: Phase

    def on_enter(self, gs: GameState):
        pass

    def get_actions(self, p_id: int, gs: GameState) -> list[Action] | None:
        raise NotImplementedError

    def next(self, gs: GameState) -> "PhaseState":
        raise NotImplementedError


class UntapPhase(PhaseState):
    phase = Phase.UNTAP

    def __init__(self):
        self.started = False

    def on_enter(self, gs: GameState) -> None:
        """Signal the start of the Untap phase;
        If optional untap, check if player has already decided to leave card tapped;
        If compelled to stay tapped, skip; else untap all cards on in-turn player's board;"""
        query = CanEnterUntapPhaseQueryEvent(gs.turn_mgr.player_turn_idx)
        gs.event_mgr.emit(query, gs)
        if query.permission is False:
            gs.phase_mgr.set_phase(Phase.UPKEEP, gs)
            return

        from models.events_all import UntapPhaseEvent
        gs.event_mgr.emit(UntapPhaseEvent(gs.turn_mgr.player_turn_idx), gs)
        for c in gs.pile_mgr.boards[gs.turn_mgr.player_turn_idx]:
            if not c.is_tapped or c.id_ in gs.turn_mgr.untap_decisions_made:
                continue
            if gs.perm_querier.can_untap(c):
                c.untap()

    def get_actions(self, p_id: int, gs: GameState):
        from models.choice_actions_all import ChoiceAction

        if not self.started:
            self.started = True
            self.on_enter(gs)

        # stack / responses during untap
        if gs.action_stack:
            if isinstance(gs.action_stack.last_action, ChoiceAction):
                return gs.action_stack.last_action.get_actions()

        self.started = False
        return None  # no player decision

    def next(self, gs: GameState):
        return UpkeepPhase()

class UpkeepPhase(PhaseState):
    phase = Phase.UPKEEP

    def on_enter(self, gs: GameState) -> None:
        from models.events_all import UpkeepEvent
        gs.event_mgr.emit(UpkeepEvent(active_player=gs.turn_mgr.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.draw_discard import MoveToDrawPhase
        # allow upkeep-triggered activations
        for c in gs.pile_mgr.boards[p_id]:
            abilities = gs.get_available_activated_abilities(c)
            if abilities:
                return [MoveToDrawPhase(p_id, gs)] + abilities

        return None  # auto-advance

    def next(self, gs: GameState):
        return DrawPhase()

class DrawPhase(PhaseState):
    phase = Phase.DRAW

    def on_enter(self, gs: GameState) -> None:
        from models.events_all import DrawStepEvent
        gs.event_mgr.emit(DrawStepEvent(active_player=gs.turn_mgr.player_turn_idx), gs)
        gs.pile_mgr.draw(gs.turn_mgr.player_turn_idx)

    def get_actions(self, p_id: int, gs: GameState):
        return None  # draw is automatic

    def next(self, gs: GameState):
        return MainPhase()

class MainPhase(PhaseState):
    phase = Phase.MAIN

    def on_enter(self, gs: GameState) -> None:
        from models.events_all import MainPhaseEvent
        gs.event_mgr.emit(MainPhaseEvent(gs.turn_mgr.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.combat import BeginCombat
        from models.actions.end_step_pass_turn import MoveToEndStep

        actions: list[Action] = []

        # required attackers constraint
        if not gs.phase_mgr.any_remaining_required_attackers(p_id, gs):
            actions.append(MoveToEndStep(p_id, gs))

        # hand actions + abilities
        actions.extend(gs.available_actions_from_hand())
        actions.extend(gs.add_activated_abilities_from_board())

        # combat option
        if any(gs.perm_querier.can_attack(c) for c in gs.pile_mgr.boards[gs.turn_mgr.player_turn_idx]):
            actions.append(BeginCombat(p_id, gs))

        # auto-advance safety:
        if all(isinstance(a, MoveToEndStep) for a in actions):
            gs.phase_mgr.set_phase(Phase.END_STEP, gs)
            return

        return actions

    def next(self, gs: GameState):
        return DeclareAttackersPhase()

class DeclareAttackersPhase(PhaseState):
    phase = Phase.DECLARE_ATTACKERS

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.combat import FinishDeclaringAttackers, CreatureAttack
        actions: list[Action] = []

        if gs.combat_mgr.combats and not gs.phase_mgr.any_remaining_required_attackers(p_id, gs):
            actions.append(FinishDeclaringAttackers(p_id, gs))

        for c in gs.pile_mgr.boards[p_id]:
            if c in gs.card_filter.attackers().result():
                continue
            if gs.perm_querier.can_attack(c):
                actions.append(CreatureAttack(p_id, gs, c))

        return actions

    def next(self, gs: GameState):
        return DeclareBlockersPhase()

class DeclareBlockersPhase(PhaseState):
    phase = Phase.DECLARE_BLOCKERS

    def on_enter(self, gs: GameState):
        from models.events_all import AttackEvent
        for com in gs.combat_mgr.combats:
            gs.event_mgr.emit(AttackEvent(com.attacker), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.combat import FinishBlocking, AssignBlocker

        if not gs.combat_mgr.combats:
            return None

        actions: list[Action] = [FinishBlocking(gs.action_on_idx, gs)]

        for blocker in gs.card_filter.on_player_board(gs.action_on_idx).creatures().result():
            for com in gs.combat_mgr.combats:
                if gs.perm_querier.can_block(blocker, com.attacker):
                    actions.append(AssignBlocker(gs.action_on_idx, gs, blocker, com.attacker))

        actions.extend(gs.available_actions_from_hand())
        actions.extend(gs.add_activated_abilities_from_board())

        # only "finish blocking" exists → auto advance
        if all(isinstance(a, FinishBlocking) for a in actions):
            return None

        return actions

    def next(self, gs: GameState):
        return PreCombatDamagePhase() if gs.combat_mgr.combats else EndStepPhase()

class PreCombatDamagePhase(PhaseState):
    phase = Phase.PRE_COMBAT_DAMAGE

    def on_enter(self, gs: GameState):
        from models.events_all import BlockEvent
        for com in gs.combat_mgr.combats:
            for blocker in com.blockers:
                gs.event_mgr.emit(BlockEvent(com.attacker, blocker), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.combat import AssignCombatDamage
        actions: list[Action] = [AssignCombatDamage(gs.action_on_idx, gs)]
        actions.extend(gs.available_actions_from_hand())
        actions.extend(gs.add_activated_abilities_from_board())

        if all(isinstance(a, AssignCombatDamage) for a in actions):
            return None

        return actions

    def next(self, gs: GameState):
        return AssignCombatDamagePhase()

class AssignCombatDamagePhase(PhaseState):
    phase = Phase.ASSIGN_COMBAT_DAMAGE

    def on_enter(self, gs: GameState):
        from models.events_all import UnblockedAttackerEvent, CombatEndEvent
        for com in gs.combat_mgr.combats:
            if not com.blockers:
                event = UnblockedAttackerEvent(com.attacker, flip(com.attacker.owner_id))
                gs.event_mgr.emit(event, gs)
            com.handle_damage()
        gs.event_mgr.emit(CombatEndEvent(active_player=gs.turn_mgr.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return SecondMainPhase()

class SecondMainPhase(PhaseState):
    phase = Phase.SECOND_MAIN

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.end_step_pass_turn import MoveToEndStep

        actions: list[Action] = [MoveToEndStep(p_id, gs)]

        # hand actions + abilities
        actions.extend(gs.available_actions_from_hand())
        actions.extend(gs.add_activated_abilities_from_board())

        # auto-advance safety:
        if all(isinstance(a, MoveToEndStep) for a in actions):
            gs.phase_mgr.set_phase(Phase.END_STEP, gs)
            return

        return actions

    def next(self, gs: GameState):
        return EndStepPhase()

class EndStepPhase(PhaseState):
    phase = Phase.END_STEP

    def on_enter(self, gs: GameState):
        from models.events_all import EndStepEvent
        gs.event_mgr.emit(EndStepEvent(active_player=gs.turn_mgr.player_turn_idx), gs)
        for c in gs.card_filter.in_play().result():
            c.modifiers.clear_eots()

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return DiscardPhase()

class DiscardPhase(PhaseState):
    phase = Phase.DISCARD

    def on_enter(self, gs: GameState):
        from models.events_all import DiscardStepEvent
        gs.event_mgr.emit(DiscardStepEvent(active_player=gs.turn_mgr.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.draw_discard import DiscardCards
        hand = gs.pile_mgr.hands[p_id]
        return [DiscardCards(p_id, gs, c) for c in hand.cards] if len(hand.cards) > 7 else None

    def next(self, gs: GameState):
        return CreaturesHealPhase()

class CreaturesHealPhase(PhaseState):
    phase = Phase.CREATURES_HEAL

    def on_enter(self, gs: GameState):
        for player_cards in gs.all_player_cards:
            for c in player_cards:
                c.damage_dealt_this_turn = 0
                c.damage_received_this_turn = 0

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return EndTurnEffectsPhase()

class EndTurnEffectsPhase(PhaseState):
    phase = Phase.END_TURN_EFFECTS

    def on_enter(self, gs: GameState):
        from models.effects.base import ActivatedAbility
        # clean up effects
        gs.event_mgr.cleanup_eot()

        for player_cards in gs.all_player_cards:
            for c in player_cards:
                c.modifiers.clear_eots()

        for pool in gs.mana_pools:
            pool.clear_floating()

        for c in gs.card_filter.result():
            for a in c.abilities:
                if isinstance(a, ActivatedAbility):
                    a.activations_this_turn = 0

        gs.combat_mgr.combats.clear()

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return PassTurnPhase()

class PassTurnPhase(PhaseState):
    phase = Phase.PASS_THE_TURN

    def on_enter(self, gs: GameState):
        from models.actions.end_step_pass_turn import PassTheTurn
        from models.events_all import PassTheTurnEvent

        current_turn_number = gs.turn_mgr.turn_number
        gs.event_mgr.emit(PassTheTurnEvent(gs.turn_mgr.player_turn_idx), gs)
        if gs.turn_mgr.turn_number != current_turn_number:  # if a PassTheTurn Listener already advanced turn
            return

        PassTheTurn(gs.turn_mgr.player_turn_idx, gs).play()

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return UntapPhase()


PHASE_MAP = {
    Phase.UNTAP: UntapPhase,
    Phase.UPKEEP: UpkeepPhase,
    Phase.DRAW: DrawPhase,
    Phase.MAIN: MainPhase,
    Phase.DECLARE_COMBAT: DeclareAttackersPhase,  # currently not in use, but there's >= 1 effect that relies on it
    Phase.DECLARE_ATTACKERS: DeclareAttackersPhase,  # declare who is attacking; tap those w/o vigil
    Phase.DECLARE_BLOCKERS: DeclareBlockersPhase,  # declare who's blocking whom
    Phase.PRE_COMBAT_DAMAGE: PreCombatDamagePhase,  # CIAA
    Phase.ASSIGN_COMBAT_DAMAGE: AssignCombatDamagePhase,
    Phase.SECOND_MAIN: SecondMainPhase,
    Phase.END_STEP: EndStepPhase,
    Phase.DISCARD: DiscardPhase,
    Phase.CREATURES_HEAL: CreaturesHealPhase,  # remove damage from perms
    Phase.END_TURN_EFFECTS: EndTurnEffectsPhase,  # end 'this turn' & 'til end of turn' effects
    Phase.PASS_THE_TURN: PassTurnPhase  # resolve end of turn effects
}

class PhaseManager:
    """Responsible for storing the current phase, getting avilable actions; can directly set phase"""
    def __init__(self, state: PhaseState = PHASE_MAP[Phase.UNTAP]):
        self.state: PhaseState = state

    @property
    def phase(self) -> Phase:
        return self.state.phase

    def set_phase(self, phase: Phase, gs: GameState):
        """Use to directly assign a particular phase & calls its on_enter() method"""
        self.state = PHASE_MAP[phase]()
        self.state.on_enter(gs)

    def get_actions(self, p_id: int, gs: GameState):
        """Gets & returns the current PhaseState's actions; if no available actions, auto-advance
        (call current PhaseState's next(), new PhaseState's on_enter() & return get_actions());
        can auto-advance through many phases if it does not have any available actions"""
        if actions := self.state.get_actions(p_id, gs):
            return actions

        self.state = self.state.next(gs)
        self.state.on_enter(gs)
        return self.get_actions(p_id, gs)

    @staticmethod
    def any_remaining_required_attackers(p_id: int, gs: GameState):
        return any(c for c in gs.pile_mgr.boards[p_id] if 'Goad' in c.keyword_abilities and gs.perm_querier.can_attack(c) and
                   c not in gs.card_filter.attackers().result())

