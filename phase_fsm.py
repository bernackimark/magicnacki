from __future__ import annotations

from abc import ABC
from enum import auto, IntEnum
from typing import TYPE_CHECKING

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
    CAST = auto()  # cast sorceries & perms; CIAA
    DECLARE_COMBAT = auto()  # CIAA
    DECLARE_ATTACKERS = auto()  # declare who is attacking; tap those w/o vigil
    DECLARE_BLOCKERS = auto()  # declare who's blocking whom
    PRE_COMBAT_DAMAGE = auto()  # CIAA
    ASSIGN_COMBAT_DAMAGE = auto()
    FIRST_STRIKE_DAMAGE = auto()  # 1st/double strike assigned; CIAA
    COMBAT_DAMAGE = auto()  # non-1st/double strike deal combat damage; CIAA
    COMBAT_END = auto()  # CIAA
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
        from models.events_all import UntapPhaseEvent
        gs.event_mgr.emit(UntapPhaseEvent(gs.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.choice_actions_all import ChoiceAction

        if not self.started:
            self.started = True
            self.on_enter(gs)

        # stack / responses during untap
        if gs.action_stack:
            if isinstance(gs.action_stack.last_action, ChoiceAction):
                return gs.action_stack.last_action.get_actions()

        # resolve untap immediately
        gs.handle_untap_phase()
        self.started = False
        return None  # no player decision

    def next(self, gs: GameState):
        return UpkeepPhase()

class UpkeepPhase(PhaseState):
    phase = Phase.UPKEEP

    def on_enter(self, gs: GameState) -> None:
        from models.events_all import UpkeepEvent
        gs.event_mgr.emit(UpkeepEvent(active_player=gs.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.draw_discard import MoveToDrawPhase
        # allow upkeep-triggered activations
        for c in gs.boards[p_id]:
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
        gs.event_mgr.emit(DrawStepEvent(active_player=gs.player_turn_idx), gs)
        gs.draw(gs.player_turn_idx)

    def get_actions(self, p_id: int, gs: GameState):
        return None  # draw is automatic

    def next(self, gs: GameState):
        return CastPhase()

class CastPhase(PhaseState):
    phase = Phase.CAST

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
        if any(gs.can_attack(c) for c in gs.boards[p_id]):
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

        if gs.combats and not gs.phase_mgr.any_remaining_required_attackers(p_id, gs):
            actions.append(FinishDeclaringAttackers(p_id, gs))

        for c in gs.boards[p_id]:
            if c in gs.card_filter.attackers().result():
                continue
            if gs.can_attack(c):
                actions.append(CreatureAttack(p_id, gs, c))

        return actions

    def next(self, gs: GameState):
        return DeclareBlockersPhase()

class DeclareBlockersPhase(PhaseState):
    phase = Phase.DECLARE_BLOCKERS

    def on_enter(self, gs: GameState):
        from models.events_all import AttackEvent
        for com in gs.combats:
            gs.event_mgr.emit(AttackEvent(com.attacker), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.combat import FinishBlocking, AssignBlocker

        if not gs.combats:
            return None

        actions: list[Action] = [FinishBlocking(gs.action_on_idx, gs)]

        for blocker in gs.card_filter.on_player_board(gs.action_on_idx).creatures().result():
            for com in gs.combats:
                if gs.can_block(blocker, com.attacker):
                    actions.append(AssignBlocker(gs.action_on_idx, gs, blocker, com.attacker))

        actions.extend(gs.available_actions_from_hand())
        actions.extend(gs.add_activated_abilities_from_board())

        # only "finish blocking" exists → auto advance
        if all(isinstance(a, FinishBlocking) for a in actions):
            return None

        return actions

    def next(self, gs: GameState):
        return PreCombatDamagePhase() if gs.combats else EndStepPhase()

class PreCombatDamagePhase(PhaseState):
    phase = Phase.PRE_COMBAT_DAMAGE

    def on_enter(self, gs: GameState):
        from models.events_all import BlockEvent
        for com in gs.combats:
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
        for com in gs.combats:
            if not com.blockers:
                event = UnblockedAttackerEvent(com.attacker, flip(com.attacker.owner_id))
                gs.event_mgr.emit(event, gs)
            com.handle_damage()
        gs.event_mgr.emit(CombatEndEvent(active_player=gs.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return EndStepPhase()

class EndStepPhase(PhaseState):
    phase = Phase.END_STEP

    def on_enter(self, gs: GameState):
        from models.events_all import EndStepEvent
        gs.event_mgr.emit(EndStepEvent(active_player=gs.player_turn_idx), gs)
        for func in gs.end_step_funcs:
            func()
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
        gs.event_mgr.emit(DiscardStepEvent(active_player=gs.player_turn_idx), gs)

    def get_actions(self, p_id: int, gs: GameState):
        from models.actions.draw_discard import DiscardCard
        hand = gs.hands[p_id]
        return [DiscardCard(p_id, gs, c) for c in hand.cards] if len(hand.cards) > 7 else None

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
        # clean up effects
        gs.until_eot_effects_and_cards.clear()
        gs.damage_preventions.clear()

        for player_cards in gs.all_player_cards:
            for c in player_cards:
                c.modifiers.clear_eots()

        for pool in gs.mana_pools:
            pool.clear_floating()

        for c in gs.card_filter.in_play().result():
            for aa in c.activated_abilities:
                aa.eff_spec.activated_cnt_this_turn = 0

        gs.combats.clear()

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return PassTurnPhase()

class PassTurnPhase(PhaseState):
    phase = Phase.PASS_THE_TURN

    def on_enter(self, gs: GameState):
        from models.actions.end_step_pass_turn import PassTheTurn
        PassTheTurn(gs.player_turn_idx, gs).play()

    def get_actions(self, p_id: int, gs: GameState):
        return None

    def next(self, gs: GameState):
        return UntapPhase()


PHASE_MAP = {
    Phase.UNTAP: UntapPhase,
    Phase.UPKEEP: UpkeepPhase,
    Phase.DRAW: DrawPhase,
    Phase.CAST: CastPhase,
    # DECLARE_COMBAT: DeclareAttackersPhase  # currently not in use, but there's at least one effect that relies on it
    Phase.DECLARE_ATTACKERS: DeclareAttackersPhase,  # declare who is attacking; tap those w/o vigil
    Phase.DECLARE_BLOCKERS: DeclareBlockersPhase,  # declare who's blocking whom
    Phase.PRE_COMBAT_DAMAGE: PreCombatDamagePhase,  # CIAA
    Phase.ASSIGN_COMBAT_DAMAGE: AssignCombatDamagePhase,
    Phase.END_STEP: EndStepPhase,
    Phase.DISCARD: DiscardPhase,
    Phase.CREATURES_HEAL: CreaturesHealPhase,  # remove damage from perms
    Phase.END_TURN_EFFECTS: EndTurnEffectsPhase,  # end 'this turn' & 'til end of turn' effects
    Phase.PASS_THE_TURN: PassTurnPhase  # resolve end of turn effects
}

class PhaseManager:
    def __init__(self, state: PhaseState = PHASE_MAP[Phase.UNTAP]):
        self.state: PhaseState = state

    @property
    def phase(self) -> Phase:
        return self.state.phase

    def set_phase(self, phase: Phase, gs: GameState):
        self.state = PHASE_MAP[phase]()  # create new state instance
        self.state.on_enter(gs)

    def get_actions(self, p_id: int, gs: GameState):
        actions = self.state.get_actions(p_id, gs)

        # If no actions, advance phase
        if actions is None:
            self.state = self.state.next(gs)
            self.state.on_enter(gs)
            return self.get_actions(p_id, gs)

        return actions

    # def get_actions(self, p_id: int, gs: GameState) -> list[Action] | None:
    #     phase = self.phase
    #     board = gs.boards[p_id]
    #
    #     if phase == Phase.UNTAP:
    #         from models.choice_actions_all import ChoiceAction
    #         from models.events_all import UntapPhaseEvent
    #         if not self._phase_started:
    #             self._phase_started = True
    #             gs.event_mgr.emit(UntapPhaseEvent(p_id), gs)
    #         if len(gs.action_stack):
    #             if isinstance(gs.action_stack.last_action, ChoiceAction):
    #                 return gs.action_stack.last_action.get_actions()
    #         else:
    #             gs.handle_untap_phase()
    #             gs._phase_started = False
    #             self.phase = Phase.UPKEEP
    #         return
    #
    #     if phase == Phase.UPKEEP:
    #         from models.actions.draw_discard import MoveToDrawPhase
    #         from models.events_all import UpkeepEvent
    #         gs.event_mgr.emit(UpkeepEvent(active_player=gs.player_turn_idx), gs)
    #         for c in board:
    #             if activated_abilities := gs.get_available_activated_abilities(c):
    #                 return [MoveToDrawPhase(c.owner_id, gs)] + activated_abilities  # type: ignore
    #         self.phase = Phase.DRAW
    #         return
    #
    #     if phase == Phase.DRAW:
    #         from models.events_all import DrawStepEvent
    #         gs.event_mgr.emit(DrawStepEvent(active_player=gs.player_turn_idx), gs)
    #         gs.draw(p_id)
    #         self.phase = Phase.CAST
    #         return
    #
    #     if phase == Phase.CAST:
    #         from models.actions.combat import BeginCombat
    #         from models.actions.end_step_pass_turn import MoveToEndStep
    #         actions: list[Action] = []
    #         if not self.any_remaining_required_attackers(p_id, gs):
    #             actions.append(MoveToEndStep(p_id, gs))  # type: ignore
    #         actions.extend(gs.available_actions_from_hand())
    #         actions.extend(gs.add_activated_abilities_from_board())  # type: ignore
    #
    #         # declare combat
    #         if any(gs.can_attack(card) for card in gs.boards[p_id]):
    #             actions.append(BeginCombat(p_id, gs))  # type: ignore
    #
    #         # if the only option is to move to end step, do so
    #         if not [a for a in actions if not isinstance(a, MoveToEndStep)]:
    #             self.phase = Phase.END_STEP
    #             return
    #
    #         return actions
    #
    #     if phase == Phase.DECLARE_ATTACKERS:
    #         from models.actions.combat import FinishDeclaringAttackers, CreatureAttack
    #         actions: list[Action] = []
    #         if gs.combats and not self.any_remaining_required_attackers(p_id, gs):
    #             actions.append(FinishDeclaringAttackers(p_id, gs))  # type: ignore
    #
    #         for c in board:
    #             if c in gs.card_filter.attackers().result():  # else vigilance creatures could be added inf times
    #                 continue
    #             if gs.can_attack(c):
    #                 actions.append(CreatureAttack(p_id, gs, c))  # type: ignore
    #         return actions
    #
    #     if phase == Phase.DECLARE_BLOCKERS:
    #         from models.actions.combat import FinishBlocking, AssignBlocker
    #         from models.events_all import AttackEvent
    #         actions: list[Action] = []
    #         for com in gs.combats:
    #             gs.event_mgr.emit(AttackEvent(com.attacker), gs)
    #
    #         # it's possible to not have any combats if something removed the attack (ex: Maze Of Ith, Mijae Djinn)
    #         # probably want to move to 2nd main, but currently rocketing right to end step
    #         if not gs.combats:
    #             self.phase = Phase.END_STEP
    #             return
    #
    #         actions.append((FinishBlocking(gs.action_on_idx, gs)))  # type: ignore
    #
    #         for blocker in gs.card_filter.on_player_board(gs.action_on_idx).creatures().result():
    #             for com in gs.combats:
    #                 if gs.can_block(blocker, com.attacker):
    #                     actions.append(AssignBlocker(gs.action_on_idx, gs, blocker, com.attacker))  # type: ignore
    #
    #         actions.extend(gs.available_actions_from_hand())
    #         actions.extend(gs.add_activated_abilities_from_board())  # type: ignore
    #
    #         # if the only option is finish blocking, auto-advance to pre-combat damage
    #         if not [a for a in actions if not isinstance(a, FinishBlocking)]:
    #             self.phase = Phase.PRE_COMBAT_DAMAGE
    #             return
    #
    #         return actions
    #
    #     if phase == Phase.PRE_COMBAT_DAMAGE:
    #         from models.actions.combat import AssignCombatDamage
    #         from models.events_all import BlockEvent
    #         actions: list[Action] = []
    #         for com in gs.combats:
    #             for blocker in com.blockers:
    #                 gs.event_mgr.emit(BlockEvent(com.attacker, blocker), gs)
    #         actions.append((AssignCombatDamage(gs.action_on_idx, gs)))  # type: ignore
    #         actions.extend(gs.available_actions_from_hand())  # type: ignore
    #         actions.extend(gs.add_activated_abilities_from_board())  # type: ignore
    #
    #         # if the only option is to Assign Combat Damage, auto-advance to Assign Combat Damage
    #         if not [a for a in actions if not isinstance(a, AssignCombatDamage)]:
    #             self.phase = Phase.ASSIGN_COMBAT_DAMAGE
    #             return
    #
    #         return actions
    #
    #     if phase == Phase.ASSIGN_COMBAT_DAMAGE:
    #         from models.events_all import UnblockedAttackerEvent, CombatEndEvent
    #         self.phase = Phase.FIRST_STRIKE_DAMAGE
    #         self.phase = Phase.COMBAT_DAMAGE
    #         for com in gs.combats:
    #             if not com.blockers:
    #                 event = UnblockedAttackerEvent(com.attacker, flip(com.attacker.owner_id))
    #                 gs.event_mgr.emit(event, gs)
    #             com.handle_damage()
    #         self.phase = Phase.COMBAT_END
    #         gs.event_mgr.emit(CombatEndEvent(active_player=gs.player_turn_idx), gs)
    #         self.phase = Phase.END_STEP
    #         return
    #
    #     if phase == Phase.END_STEP:
    #         from models.events_all import EndStepEvent
    #         gs.event_mgr.emit(EndStepEvent(active_player=gs.player_turn_idx), gs)
    #
    #         # execute all end step funcs
    #         for func in gs.end_step_funcs:
    #             func()
    #
    #         for c in gs.card_filter.in_play().result():
    #             c.modifiers.clear_eots()
    #         self.phase = Phase.DISCARD
    #         return
    #
    #     if phase == Phase.DISCARD:
    #         from models.actions.draw_discard import DiscardCard
    #         from models.events_all import DiscardStepEvent
    #         hand = gs.hands[p_id]
    #         gs.event_mgr.emit(DiscardStepEvent(active_player=gs.player_turn_idx), gs)
    #         if len(hand.cards) > 7:
    #             return [DiscardCard(gs.player_turn_idx, gs, c) for c in hand.cards]  # type: ignore
    #         self.phase = Phase.CREATURES_HEAL
    #         return
    #
    #     if phase == Phase.CREATURES_HEAL:
    #         # THIS NEEDS A RE-WRITE:
    #         # 1) I don't want to use decks_all_cards
    #         # 2) doesn't feel the right way to expire expiring damage
    #         for player_cards in gs.all_player_cards:
    #             for c in player_cards:
    #                 c.damage_dealt_this_turn = 0
    #                 c.damage_received_this_turn = 0
    #         self.phase = Phase.END_TURN_EFFECTS
    #         return
    #
    #     if phase == Phase.END_TURN_EFFECTS:
    #         # new approach
    #         for eff, card in gs.until_eot_effects_and_cards:
    #             if eff in gs.damage_preventions:
    #                 gs.until_eot_effects_and_cards = [i for i in gs.until_eot_effects_and_cards if i != eff]
    #         gs.until_eot_effects_and_cards.clear()
    #
    #         # Expire all temporary damage prevention
    #         gs.damage_preventions.clear()
    #         # Clear temp modifiers
    #         for player_cards in gs.all_player_cards:
    #             for c in player_cards:
    #                 c.modifiers.clear_eots()
    #         # Empty mana pools
    #         for pool in gs.mana_pools:
    #             pool.clear_floating()
    #         # Reset all activated ability counts to 0 (ex: fire-drake {R}: +1/+0; Activate only once each turn.)
    #         for c in gs.card_filter.in_play().result():
    #             for aa in c.activated_abilities:
    #                 aa.eff_spec.activated_cnt_this_turn = 0
    #         # clear combats
    #         gs.combats.clear()
    #         self.phase = Phase.PASS_THE_TURN
    #         return
    #
    #     if phase == Phase.PASS_THE_TURN:
    #         from models.actions.end_step_pass_turn import PassTheTurn
    #         PassTheTurn(p_id, gs).play()
    #         return

    @staticmethod
    def any_remaining_required_attackers(p_id: int, gs: GameState):
        return any(c for c in gs.boards[p_id] if 'Goad' in c.keyword_abilities and gs.can_attack(c) and
                   c not in gs.card_filter.attackers().result())

