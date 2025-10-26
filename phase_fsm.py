from dataclasses import dataclass, field
from enum import Enum, auto

class Phase(Enum):
    NEW_SESSION = auto()  # roll dice; decide going first
    DICE_ROLL = auto()
    NEW_GAME = auto()  # shuffle; deal; mulligan
    UNTAP = auto()  # (phasing happens, if relevant); untap permanents
    UPKEEP = auto()  # any player can cast instants & activate abilities (CIAA)
    DRAW = auto()  # draw a card; any player can CIAA
    CAST = auto()  # cast sorceries & perms; CIAA
    DECLARE_COMBAT = auto()  # CIAA
    DECLARE_ATTACKERS = auto()  # declare who is attacking; tap those w/o vigil
    DECLARE_BLOCKERS = auto()  # declare who's blocking whom
    ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES = auto()  # CIAA
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

# @dataclass
# class PhaseStateMachine:
#     player_turn_idx: int
#     player_cnt: int
#     phase: Phase = Phase.NEW_SESSION
#     turn_num: int = 1
#     round_num: int = 1
#     in_turn_player_available_actions: list[Action] = field(default=Action.START_GAME)
#     out_turn_player_available_actions: list[Action] = field(default=Action.START_GAME)
#     player_action_idx: int = None
#
#     def transition(self, player_idx: int, action: Action) -> None:
#         print(f"Current state; {self.phase.value}; received this {action.value}")
#         if self.phase == Phase.NEW_SESSION:
#             if action == Action.START_GAME:
#                 self.phase = Phase.DICE_ROLL
#                 self.in_turn_player_available_actions = [Action.ROLL_DICE]
#                 self.out_turn_player_available_actions = [Action.ROLL_DICE]
#         if self.phase == Phase.DICE_ROLL:
#             if action == Action.PLAY_FIRST:
#                 self.player_turn_idx = player_idx
#             elif action == Action.PLAY_SECOND:
#                 self.player_turn_idx = 1 if player_idx == 0 else 1
#             self.in_turn_player_available_actions = [Action.TAKE_MULLIGAN, Action.KEEP_HAND]
#             self.out_turn_player_available_actions = [Action.TAKE_MULLIGAN, Action.KEEP_HAND]
#             self.phase = Phase.NEW_GAME
#             ...  # shuffle, 1st play decided by dice roll, mulligan
#         if self.phase == Phase.NEW_GAME:
#             self.phase = Phase.UNTAP
#             self.in_turn_player_available_actions = []
#             self.out_turn_player_available_actions = []
#             # we head into the untap phase
#         if self.phase == Phase.UNTAP:
#             self.phase = Phase.UPKEEP
#             self.in_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#             self.out_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#             ...  # game engine does everything and auto-transitions to next
#         if self.phase == Phase.UPKEEP:
#             self.phase = Phase.DRAW
#             self.in_turn_player_available_actions = [Action.DRAW]  # TODO: so long as it's not the 1st turn of game, player can draw
#             self.out_turn_player_available_actions = []
#             ...  # any player can cast instants & activate abilities (CIAA)
#         if self.phase == Phase.DRAW:
#             self.phase = Phase.CAST
#             self.in_turn_player_available_actions = [Action.PLAY_PERM_AND_SORCERY, Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY, Action.DECLARE_COMBAT, Action.MOVE_TO_END_STEP]
#             self.out_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#             ...  # in-turn player draws; CIAA
#             ...  # first player of game doesn't draw
#             ...  # in-turn player can play land; no CIAA
#         if self.phase == Phase.CAST:
#             if action == Action.DECLARE_COMBAT:
#                 self.phase = Phase.DECLARE_COMBAT
#                 self.in_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#                 self.out_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#             elif action == Action.MOVE_TO_END_STEP:
#                 self.phase = Phase.END_STEP
#                 self.in_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#                 self.out_turn_player_available_actions = [Action.PLAY_INSTANT_AND_ACTIVATE_ABILITY]
#
#         # TODO: THIS IS WHERE I STOPPED.  THIS IS PRETTY CONFUSING.
#         #  COULD I JUST A HAVE DICTIONARY OF PHASES AND POSSIBLE ACTIONS?
#         #  EX: {Phase.CAST:
#         #          {IN_TURN_PLAYER: (Action A, Action B, Action C),
#         #           OUT_TURN_PLAYER: (Action A)},
#         #       Phase.SOMEONE_PLAYED_AN_INSTANT:
#         #           {THE_GUY_WHO_PLAYED_THE_INSTANT: (),
#         #            THE_OTHER_GUY: (Action A)}
#         #     }
#
#
#         if self.phase == Phase.DECLARE_COMBAT:
#             self.phase = Phase.DECLARE_ATTACKERS
#             ...  # CIAA
#         if self.phase == Phase.DECLARE_ATTACKERS:
#             self.phase = Phase.DECLARE_BLOCKERS
#             ...  # in-turn player declares who's attacking; tap non-vigils
#         if self.phase == Phase.DECLARE_BLOCKERS:
#             self.phase = Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES
#             ...  # out-turn player declares who's blocking whom
#         if self.phase == Phase.ATTACK_AND_BLOCK_INSTANTS_AND_ABILITIES:
#             self.phase = Phase.FIRST_STRIKE_DAMAGE
#             ...  # CIAA
#         if self.phase == Phase.FIRST_STRIKE_DAMAGE:
#             self.phase = Phase.COMBAT_DAMAGE
#             ...  # 1st/double strike assigned; CIAA
#         if self.phase == Phase.COMBAT_DAMAGE:
#             self.phase = Phase.COMBAT_END
#             ...  # non-1st/double strike deal combat damage; CIAA
#         if self.phase == Phase.COMBAT_END:
#             self.phase = Phase.END_STEP
#             ...  # CIAA
#         if self.phase == Phase.END_STEP:
#             self.phase = Phase.DISCARD
#             ...  # CIAA; last action for either player (except discard)
#         if self.phase == Phase.DISCARD:
#             self.phase = Phase.CREATURES_HEAL
#             ...  # game engine determines if this step is required
#         if self.phase == Phase.CREATURES_HEAL:
#             self.phase = Phase.END_TURN_EFFECTS
#             ...  # no humans can play; remove damage from perms
#         if self.phase == Phase.END_TURN_EFFECTS:
#             self.phase = Phase.PASS_THE_TURN
#             ...  # no humans can play; end 'this turn' & 'til end of turn' effects
#         if self.phase == Phase.PASS_THE_TURN:
#             ...  # no human can play; set back to UNTAP
#             if not (self.turn_num - 1) % self.player_cnt:
#                 self.round_num += 1
#             self.turn_num += 1
#             self.player_turn_idx += 1 if not self.player_turn_idx == self.player_cnt else 0
#             self.phase = Phase.UNTAP
#             self.action_for_noone()
#
#     def action_for_noone(self) -> None:
#         self.in_turn_player_can_action = False
#         self.out_turn_player_can_action = False
#
#     def action_for_anyone(self) -> None:
#         self.in_turn_player_can_action = True
#         self.out_turn_player_can_action = True
#
#     def action_for_in_turn(self) -> None:
#         self.in_turn_player_can_action = True
#         self.out_turn_player_can_action = False
#
#     def action_for_out_turn(self) -> None:
#         self.in_turn_player_can_action = False
#         self.out_turn_player_can_action = True



