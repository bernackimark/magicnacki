from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.constants import KW
from models.events_all import StateBasedEvent
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

"""
1) Beginning of Combat Step:
 - Players can cast spells and activate abilities before attackers are declared.
2) Declare Attackers Step:
 - You choose which creatures attack.
 - You then receive priority to cast spells.
3) Declare Blockers Step:
 - Your opponent chooses blocking creatures.
 - Afterward, players can cast spells (e.g., pumping your creature or casting removal)
4) First Strike Combat Damage Step:
 - If any attacking or blocking creature has first strike or double strike, this step is created.
 - Only these creatures assign and deal combat damage.
 - Check State-Based Actions First: Dead creatures moved to the graveyard immediately.
 - The player whose turn it is gets the first chance to cast a spell, followed by the defending player.
 - The game will not move to the normal combat damage step until both players pass priority without doing anything
5) Normal Combat Damage Step:
 - Instead of proceeding to the end of combat, a second damage step occurs.
 - All remaining attacking and blocking creatures (those without first strike in the previous step) deal their damage.
 - Creatures with double strike also deal their damage here.
"""

@dataclass
class Combat:
    attacker: GameCard
    _blockers: list[GameCard] = field(default_factory=list)
    is_blocked: bool = False  # Once a blocker has been declared, this never becomes False
    _declared_attacker: GameCard | None = None  # logs the attacker even if it's been removed later
    _all_declared_blockers: list[GameCard] = field(default_factory=list)  # logs ALL blockers added

    def __post_init__(self):
        self._declared_attacker = self.attacker

    def __repr__(self):
        return f"{self.attacker} attacking {self.blockers}"

    @property
    def blockers(self) -> list[GameCard | None]:
        """The current blockers in this combat; doesn't include those who have been removed through damage or removal"""
        return self._blockers

    @property
    def declared_attacker(self) -> GameCard:
        """Always returns this combat's attacker, even if it's been removed"""
        return self._declared_attacker

    @property
    def all_declared_blockers(self) -> list[GameCard | None]:
        """All blockers ever in this combat, including those removed through damage or removal"""
        return self._all_declared_blockers

    def add_blocker(self, blocker: GameCard):
        self._blockers.append(blocker)
        self.all_declared_blockers.append(blocker)
        self.is_blocked = True

# @dataclass
# class Combat:
#     _gs: GameState
#     attacker: GameCard
#     blockers: list[GameCard] = field(default_factory=list)
#
#     def __repr__(self):
#         return f"{self.attacker} attacking {self.blockers}"
#
#     @property
#     def contains_first_strike(self) -> bool:
#         return any(KW.FIRST_STRIKE in self.attacker.keyword_abilities or
#                    KW.FIRST_STRIKE in b.keyword_abilities for b in self.blockers)
#
#     @property
#     def defending_player(self) -> int:
#         return flip(self.attacker.owner_id)
#
#     def handle_damage(self):
#         """Main entry point for combat damage resolution. Handles first strike & normal damage & unblocked attackers.
#         Currently, all attacker damage is assigned to the first blocker, no damage splitting supported yet"""
#         if self.contains_first_strike:
#             # First strike phase
#             self._combat_phase(first_strike=True)
#
#         # Normal damage phase (skip assigning damage by first strikers, who already dealt damage)
#         self._combat_phase(first_strike=False)
#
#     def _combat_phase(self, first_strike: bool):
#         """Resolves damage for a phase (first strike or normal)"""
#         damage_assignments = []  # (source, amount, target)
#
#         # --- No blockers ---
#         if not self.blockers:
#             if not first_strike:
#                 damage_assignments.append((self.attacker, self.attacker.power, self.defending_player))
#
#         else:
#             # --- Attacker → blocker ---
#             a = self.attacker
#             if self._phase_applicable(a, first_strike):
#                 if len(self.blockers) > 1 and a.rampage_amt:
#                     multiplier = len(self.blockers) - 1
#                     a.modifiers.append(PTMod(s=a, p_adj=a.rampage_amt * multiplier,
#                                              t_adj=a.rampage_amt * multiplier, expires='EOT'))
#
#                 target = self.blockers[0]
#                 # If blocker is not on the battlefield (destroyed/bounced), it will not receive a damage assignment
#                 if target.zone == Zone.BATTLEFIELD:
#                     if self._gs.perm_querier.can_damage(target, a):
#                         damage_assignments.append((a, a.power, target))
#
#             # --- Blockers → attacker ---
#             for blocker in self.blockers:
#                 if self._phase_applicable(blocker, first_strike):
#                     if self._gs.perm_querier.can_damage(self.attacker, blocker):
#                         damage_assignments.append((blocker, blocker.power, self.attacker))
#
#         # --- apply damage ---
#         for source, amount, target in damage_assignments:
#             self._gs.apply_damage(source, amount, target, is_combat=True)
#
#         # --- run SBEs ---
#         self._gs.event_mgr.emit(StateBasedEvent())
#         # self.gs.check_state_based_actions()
#
#     @staticmethod
#     def _phase_applicable(creature: GameCard, first_strike: bool) -> bool:
#         """Returns True if this creature should deal damage in the current phase."""
#         if not first_strike and KW.FIRST_STRIKE not in creature.keyword_abilities:
#             return True
#         if first_strike and KW.FIRST_STRIKE in creature.keyword_abilities:
#             return True
#         return False


class CombatManager:
    def __init__(self, gs: GameState):
        self._gs = gs
        self.combats: list[Combat] = []

    @property
    def attackers(self) -> list[GameCard | None]:
        return [com.attacker for com in self.combats]

    @property
    def blockers(self) -> list[GameCard | None]:
        return [b for com in self.combats for b in com.blockers]

    def create_combat(self, attacker: GameCard) -> None:
        self.combats.append(Combat(attacker))

    def add_blocker(self, attacker: GameCard, blocker: GameCard):
        combat = self.get_combat(attacker)
        if not combat:
            raise ValueError(f"Combat featuring {attacker} not found")
        combat.add_blocker(blocker)

    def get_combat(self, c: GameCard) -> Combat | None:
        for com in self.combats:
            if c is com.declared_attacker or c in com.all_declared_blockers:
                return com

    def handle_damage_step(self, is_first_strike: bool):
        """Resolve one combat damage step"""
        self._handle_damage(is_first_strike)

    def get_combatants_against(self, c: GameCard) -> list[GameCard | None]:
        com = self.get_combat(c)
        if not com:
            return []
        if com.declared_attacker is c:
            return [b for b in com.all_declared_blockers]
        if c in com.all_declared_blockers:
            return [com.declared_attacker]

    def remove_from_combat(self, c: GameCard):
        """If attacker, untap attacker & set combat.attacker to None;
        If a blocking creature is destroyed/bounced after it is declared as a blocker, the attacking creature remains
        blocked and will deal no damage, unless it has trample"""
        for combat in list(self.combats):
            if combat.attacker is c:
                combat.attacker.untap()
                combat.attacker = None
                return
            if c in combat.blockers:
                combat.blockers.remove(c)
                return

    def is_in_combat(self, creature: GameCard):
        for combat in self.combats:
            if combat.attacker is creature:
                return True
            if creature in combat.blockers:
                return True
        return False

    @staticmethod
    def _deals_damage_this_step(creature: GameCard, first_strike: bool) -> bool:
        has_fs = KW.FIRST_STRIKE in creature.keyword_abilities
        return has_fs if first_strike else not has_fs

    @property
    def has_first_strike_step(self):
        for combat in self.combats:
            if KW.FIRST_STRIKE in combat.attacker.keyword_abilities:
                return True
            for blocker in combat.blockers:
                if KW.FIRST_STRIKE in blocker.keyword_abilities:
                    return True
        return False

    def _handle_damage(self, first_strike: bool):
        assignments: list[tuple[GameCard, int, GameCard | int]] = []
        for combat in self.combats:
            attacker = combat.attacker
            # attacker removed from combat
            if not self.is_in_combat(attacker):
                continue

            # attacker -> blocker/player
            if attacker and self._deals_damage_this_step(attacker, first_strike):
                attacker_power = attacker.power

                # Rampage
                if attacker.rampage_amt and len(combat.blockers) > 1:
                    bonus = attacker.rampage_amt * (len(combat.blockers) - 1)
                    attacker_power += bonus

                if combat.blockers:
                    blocker = combat.blockers[0]
                    if self.is_in_combat(blocker):
                        # handle trample
                        if KW.TRAMPLE in attacker.keyword_abilities:
                            lethal = max(0, blocker.toughness - blocker.damage_received_this_turn)
                            damage_to_blocker = min(attacker_power, lethal)
                            assignments.append((attacker, damage_to_blocker, blocker))
                            excess = attacker_power - damage_to_blocker
                            if excess > 0:
                                assignments.append((attacker, excess, flip(attacker.owner_id)))
                        else:
                            assignments.append((attacker, attacker.power, blocker))
                    else:
                        # Trample still hits player even if blockers are gone
                        if KW.TRAMPLE in attacker.keyword_abilities:
                            assignments.append((attacker, attacker_power, flip(attacker.owner_id)))

                elif not combat.is_blocked:
                    assignments.append((attacker, attacker.power, flip(attacker.owner_id)))

            # blockers -> attacker
            for blocker in combat.blockers:
                if not self.is_in_combat(blocker):
                    continue
                if self._deals_damage_this_step(blocker, first_strike):
                    assignments.append((blocker, blocker.power, attacker))

        # deal damage
        for source, amount, target in assignments:
            if source is not None and target is not None:
                if self._gs.perm_querier.can_damage(target, source):
                    self._gs.apply_damage(source, amount, target, is_combat=True)

        self._gs.event_mgr.emit(StateBasedEvent())
