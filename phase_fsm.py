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
    def __init__(self, gs: GameState):
        self.gs = gs

    def get_actions(self, p_id: int) -> list[Action] | None:
        phase = self.gs.phase
        board = self.gs.boards[p_id]

        if phase == Phase.UNTAP:
            from models.choice_actions_all import ChoiceAction
            from models.events_all import UntapPhaseEvent
            if not self.gs._phase_started:
                self.gs._phase_started = True
                self.gs.emit(UntapPhaseEvent(p_id))
            if len(self.gs.action_stack):
                if isinstance(self.gs.action_stack.last_action, ChoiceAction):
                    return self.gs.action_stack.last_action.get_actions()
            else:
                self.gs.handle_untap_phase()
                self.gs._phase_started = False
                self.gs.phase = Phase.UPKEEP
            return

        if phase == Phase.UPKEEP:
            from models.actions.draw_discard import MoveToDrawPhase
            from models.events_all import UpkeepEvent
            self.gs.emit(UpkeepEvent(active_player=self.gs.player_turn_idx))
            for c in board:
                if activated_abilities := self.gs.get_available_activated_abilities(c):
                    return [MoveToDrawPhase(c.owner_id, self.gs)] + activated_abilities  # type: ignore
            self.gs.phase = Phase.DRAW
            return

        if phase == Phase.DRAW:
            from models.events_all import DrawStepEvent
            self.gs.emit(DrawStepEvent(active_player=self.gs.player_turn_idx))
            self.gs.draw(p_id)
            self.gs.phase = Phase.CAST
            return

        if phase == Phase.CAST:
            from models.actions.combat import BeginCombat
            from models.actions.end_step_pass_turn import MoveToEndStep
            actions: list[Action] = []
            if not self.any_remaining_required_attackers(p_id):
                actions.append(MoveToEndStep(p_id, self.gs))  # type: ignore
            actions.extend(self.gs.available_actions_from_hand())
            actions.extend(self.gs.add_activated_abilities_from_board())  # type: ignore

            # declare combat
            if any(self.gs.can_attack(card) for card in self.gs.boards[p_id]):
                actions.append(BeginCombat(p_id, self.gs))  # type: ignore
            return actions

        if phase == Phase.DECLARE_ATTACKERS:
            from models.actions.combat import FinishDeclaringAttackers, CreatureAttack
            actions: list[Action] = []
            if self.gs.combats and not self.any_remaining_required_attackers(p_id):
                actions.append(FinishDeclaringAttackers(p_id, self.gs))  # type: ignore

            for c in board:
                if c in self.gs.card_filter.attackers().result():  # else vigilance creatures could be added inf times
                    continue
                if self.gs.can_attack(c):
                    actions.append(CreatureAttack(p_id, self.gs, c))  # type: ignore
            return actions

        if phase == Phase.DECLARE_BLOCKERS:
            from models.actions.combat import FinishBlocking, AssignBlocker
            from models.events_all import AttackEvent
            actions: list[Action] = []
            for com in self.gs.combats:
                self.gs.emit(AttackEvent(com.attacker))

            # it's possible to not have any combats if something removed the attack (ex: Maze Of Ith, Mijae Djinn)
            # probably want to move to 2nd main, but currently rocketing right to end step
            if not self.gs.combats:
                self.gs.phase = Phase.END_STEP
                return

            actions.append((FinishBlocking(self.gs.action_on_idx, self.gs)))  # type: ignore

            for blocker in self.gs.card_filter.on_player_board(self.gs.action_on_idx).creatures().result():
                for com in self.gs.combats:
                    if self.gs.can_block(blocker, com.attacker):
                        actions.append(AssignBlocker(self.gs.action_on_idx, self.gs, blocker, com.attacker))  # type: ignore

            actions.extend(self.gs.available_actions_from_hand())
            actions.extend(self.gs.add_activated_abilities_from_board())  # type: ignore
            return actions

        if phase == Phase.PRE_COMBAT_DAMAGE:
            from models.actions.combat import AssignCombatDamage
            from models.events_all import BlockEvent
            actions: list[Action] = []
            for com in self.gs.combats:
                for blocker in com.blockers:
                    self.gs.emit(BlockEvent(com.attacker, blocker))
            actions.append((AssignCombatDamage(self.gs.action_on_idx, self.gs)))  # type: ignore
            actions.extend(self.gs.available_actions_from_hand())  # type: ignore
            actions.extend(self.gs.add_activated_abilities_from_board())  # type: ignore
            return actions

        if phase == Phase.ASSIGN_COMBAT_DAMAGE:
            from models.events_all import UnblockedAttackerEvent, CombatEndEvent
            self.gs.phase = Phase.FIRST_STRIKE_DAMAGE
            self.gs.phase = Phase.COMBAT_DAMAGE
            for com in self.gs.combats:
                if not com.blockers:
                    event = UnblockedAttackerEvent(com.attacker, flip(com.attacker.owner_id))
                    self.gs.emit(event)
                com.handle_damage()
            self.gs.phase = Phase.COMBAT_END
            self.gs.emit(CombatEndEvent(active_player=self.gs.player_turn_idx))
            self.gs.phase = Phase.END_STEP
            return

        if phase == Phase.END_STEP:
            from models.events_all import EndStepEvent
            self.gs.emit(EndStepEvent(active_player=self.gs.player_turn_idx))

            # execute all end step funcs
            for func in self.gs.end_step_funcs:
                func()

            for c in self.gs.card_filter.in_play().result():
                c.modifiers.clear_temps()
            self.gs.phase = Phase.DISCARD
            return

        if phase == Phase.DISCARD:
            from models.actions.draw_discard import DiscardCard
            from models.events_all import DiscardStepEvent
            hand = self.gs.hands[p_id]
            self.gs.emit(DiscardStepEvent(active_player=self.gs.player_turn_idx))
            if len(hand.cards) > 7:
                return [DiscardCard(self.gs.player_turn_idx, self.gs, c) for c in hand.cards]  # type: ignore
            self.gs.phase = Phase.CREATURES_HEAL
            return

        if phase == Phase.CREATURES_HEAL:
            # THIS NEEDS A RE-WRITE:
            # 1) I don't want to use decks_all_cards
            # 2) doesn't feel the right way to expire expiring damage
            for deck in self.gs.decks_all_cards:
                for c in deck.cards:
                    c.damage_dealt_this_turn = 0
                    c.damage_received_this_turn = 0
            self.gs.phase = Phase.END_TURN_EFFECTS
            return

        if phase == Phase.END_TURN_EFFECTS:
            # new approach
            for eff, card in self.gs.until_eot_effects_and_cards:
                if eff in self.gs.damage_preventions:
                    self.gs.until_eot_effects_and_cards = [i for i in self.gs.until_eot_effects_and_cards if i != eff]
            self.gs.until_eot_effects_and_cards.clear()

            # Expire all temporary damage prevention
            self.gs.damage_preventions.clear()
            # Clear temp modifiers
            for d in self.gs.decks_all_cards:
                for c in d.cards:
                    c.modifiers.clear_temps()
            # Empty mana pools
            for pool in self.gs.mana_pools:
                pool.clear_floating()
            # Reset all activated ability counts to 0 (ex: fire-drake {R}: +1/+0; Activate only once each turn.)
            for c in self.gs.card_filter.in_play().result():
                for aa in c.activated_abilities:
                    aa.eff_spec.activated_cnt_this_turn = 0
            # clear combats
            self.gs.combats.clear()
            self.gs.phase = Phase.PASS_THE_TURN
            return

        if phase == Phase.PASS_THE_TURN:
            from models.actions.end_step_pass_turn import PassTheTurn
            PassTheTurn(p_id, self.gs).play()
            return

    def any_remaining_required_attackers(self, p_id: int):
        return any(c for c in self.gs.boards[p_id] if 'Goad' in c.keyword_abilities and self.gs.can_attack(c) and
                   c not in self.gs.card_filter.attackers().result())

