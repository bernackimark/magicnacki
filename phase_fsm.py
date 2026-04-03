from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto, IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

from models.utils import flip

class Phase(IntEnum):
    NEW_SESSION = auto()  # roll dice; decide going first
    DICE_ROLL = auto()
    SIDEBOARDING = auto()
    NEW_GAME = auto()  # shuffle; deal; mulligan
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

@dataclass
class Action(Enum):
    START_GAME = auto()
    ROLL_DICE = auto()
    PLAY_FIRST = auto()
    PLAY_SECOND = auto()
    DECIDE_FIRST_OR_SECOND = auto()
    TAKE_MULLIGAN = auto()
    KEEP_HAND = auto()
    DRAW = auto()
    PLAY_PERM_AND_SORCERY = auto()
    PLAY_INSTANT_AND_ACTIVATE_ABILITY = auto()
    DECLARE_COMBAT = auto()
    CHOOSE_ATTACKERS = auto()
    FINISH_DECLARING_ATTACKERS = auto()
    CHOOSE_BLOCKERS = auto()
    FINISH_DECLARING_BLOCKERS = auto()
    MOVE_TO_END_STEP = auto()
    DISCARD = auto()
    PASS_THE_TURN = auto()


class PhaseManager:
    def __init__(self, phase: Phase):
        self.phase = phase
        self._phase_started: bool = False

    def get_actions(self, p_id: int, gs: GameState) -> list[Action] | None:
        phase = self.phase
        board = gs.boards[p_id]

        if phase == Phase.UNTAP:
            from models.choice_actions_all import ChoiceAction
            from models.events_all import UntapPhaseEvent
            if not self._phase_started:
                self._phase_started = True
                gs.emit(UntapPhaseEvent(p_id))
            if len(gs.action_stack):
                if isinstance(gs.action_stack.last_action, ChoiceAction):
                    return gs.action_stack.last_action.get_actions()
            else:
                gs.handle_untap_phase()
                gs._phase_started = False
                gs.phase = Phase.UPKEEP
            return

        if phase == Phase.UPKEEP:
            from models.actions.draw_discard import MoveToDrawPhase
            from models.events_all import UpkeepEvent
            gs.emit(UpkeepEvent(active_player=gs.player_turn_idx))
            for c in board:
                if activated_abilities := gs.get_available_activated_abilities(c):
                    return [MoveToDrawPhase(c.owner_id, gs)] + activated_abilities  # type: ignore
            gs.phase = Phase.DRAW
            return

        if phase == Phase.DRAW:
            from models.events_all import DrawStepEvent
            gs.emit(DrawStepEvent(active_player=gs.player_turn_idx))
            gs.draw(p_id)
            gs.phase = Phase.CAST
            return

        if phase == Phase.CAST:
            from models.actions.combat import BeginCombat
            from models.actions.end_step_pass_turn import MoveToEndStep
            actions: list[Action] = []
            if not self.any_remaining_required_attackers(p_id, gs):
                actions.append(MoveToEndStep(p_id, gs))  # type: ignore
            actions.extend(gs.available_actions_from_hand())
            actions.extend(gs.add_activated_abilities_from_board())  # type: ignore

            # declare combat
            if any(gs.can_attack(card) for card in gs.boards[p_id]):
                actions.append(BeginCombat(p_id, gs))  # type: ignore
            return actions

        if phase == Phase.DECLARE_ATTACKERS:
            from models.actions.combat import FinishDeclaringAttackers, CreatureAttack
            actions: list[Action] = []
            if gs.combats and not self.any_remaining_required_attackers(p_id, gs):
                actions.append(FinishDeclaringAttackers(p_id, gs))  # type: ignore

            for c in board:
                if c in gs.card_filter.attackers().result():  # else vigilance creatures could be added inf times
                    continue
                if gs.can_attack(c):
                    actions.append(CreatureAttack(p_id, gs, c))  # type: ignore
            return actions

        if phase == Phase.DECLARE_BLOCKERS:
            from models.actions.combat import FinishBlocking, AssignBlocker
            from models.events_all import AttackEvent
            actions: list[Action] = []
            for com in gs.combats:
                gs.emit(AttackEvent(com.attacker))

            # it's possible to not have any combats if something removed the attack (ex: Maze Of Ith, Mijae Djinn)
            # probably want to move to 2nd main, but currently rocketing right to end step
            if not gs.combats:
                gs.phase = Phase.END_STEP
                return

            actions.append((FinishBlocking(gs.action_on_idx, gs)))  # type: ignore

            for blocker in gs.card_filter.on_player_board(gs.action_on_idx).creatures().result():
                for com in gs.combats:
                    if gs.can_block(blocker, com.attacker):
                        actions.append(AssignBlocker(gs.action_on_idx, gs, blocker, com.attacker))  # type: ignore

            actions.extend(gs.available_actions_from_hand())
            actions.extend(gs.add_activated_abilities_from_board())  # type: ignore
            return actions

        if phase == Phase.PRE_COMBAT_DAMAGE:
            from models.actions.combat import AssignCombatDamage
            from models.events_all import BlockEvent
            actions: list[Action] = []
            for com in gs.combats:
                for blocker in com.blockers:
                    gs.emit(BlockEvent(com.attacker, blocker))
            actions.append((AssignCombatDamage(gs.action_on_idx, gs)))  # type: ignore
            actions.extend(gs.available_actions_from_hand())  # type: ignore
            actions.extend(gs.add_activated_abilities_from_board())  # type: ignore
            return actions

        if phase == Phase.ASSIGN_COMBAT_DAMAGE:
            from models.events_all import UnblockedAttackerEvent, CombatEndEvent
            gs.phase = Phase.FIRST_STRIKE_DAMAGE
            gs.phase = Phase.COMBAT_DAMAGE
            for com in gs.combats:
                if not com.blockers:
                    event = UnblockedAttackerEvent(com.attacker, flip(com.attacker.owner_id))
                    gs.emit(event)
                com.handle_damage()
            gs.phase = Phase.COMBAT_END
            gs.emit(CombatEndEvent(active_player=gs.player_turn_idx))
            gs.phase = Phase.END_STEP
            return

        if phase == Phase.END_STEP:
            from models.events_all import EndStepEvent
            gs.emit(EndStepEvent(active_player=gs.player_turn_idx))

            # execute all end step funcs
            for func in gs.end_step_funcs:
                func()

            for c in gs.card_filter.in_play().result():
                c.modifiers.clear_temps()
            gs.phase = Phase.DISCARD
            return

        if phase == Phase.DISCARD:
            from models.actions.draw_discard import DiscardCard
            from models.events_all import DiscardStepEvent
            hand = gs.hands[p_id]
            gs.emit(DiscardStepEvent(active_player=gs.player_turn_idx))
            if len(hand.cards) > 7:
                return [DiscardCard(gs.player_turn_idx, gs, c) for c in hand.cards]  # type: ignore
            gs.phase = Phase.CREATURES_HEAL
            return

        if phase == Phase.CREATURES_HEAL:
            # THIS NEEDS A RE-WRITE:
            # 1) I don't want to use decks_all_cards
            # 2) doesn't feel the right way to expire expiring damage
            for deck in gs.decks_all_cards:
                for c in deck.cards:
                    c.damage_dealt_this_turn = 0
                    c.damage_received_this_turn = 0
            gs.phase = Phase.END_TURN_EFFECTS
            return

        if phase == Phase.END_TURN_EFFECTS:
            # new approach
            for eff, card in gs.until_eot_effects_and_cards:
                if eff in gs.damage_preventions:
                    gs.until_eot_effects_and_cards = [i for i in gs.until_eot_effects_and_cards if i != eff]
            gs.until_eot_effects_and_cards.clear()

            # Expire all temporary damage prevention
            gs.damage_preventions.clear()
            # Clear temp modifiers
            for d in gs.decks_all_cards:
                for c in d.cards:
                    c.modifiers.clear_temps()
            # Empty mana pools
            for pool in gs.mana_pools:
                pool.clear_floating()
            # Reset all activated ability counts to 0 (ex: fire-drake {R}: +1/+0; Activate only once each turn.)
            for c in gs.card_filter.in_play().result():
                for aa in c.activated_abilities:
                    aa.eff_spec.activated_cnt_this_turn = 0
            # clear combats
            gs.combats.clear()
            gs.phase = Phase.PASS_THE_TURN
            return

        if phase == Phase.PASS_THE_TURN:
            from models.actions.end_step_pass_turn import PassTheTurn
            PassTheTurn(p_id, gs).play()
            return

    @staticmethod
    def any_remaining_required_attackers(p_id: int, gs: GameState):
        return any(c for c in gs.boards[p_id] if 'Goad' in c.keyword_abilities and gs.can_attack(c) and
                   c not in gs.card_filter.attackers().result())

