from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.modifiers import PTMod
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


@dataclass
class Combat:
    gs: GameState
    attacker: GameCard
    blockers: list[GameCard] = field(default_factory=list)

    def __repr__(self):
        return f"{self.attacker} attacking {self.blockers}"

    def handle_damage(self):
        """Main entry point for combat damage resolution. Handles first strike & normal damage & unblocked attackers.
        Currently, all attacker damage is assigned to the first blocker, no damage splitting supported yet"""
        if self._has_first_strike(self.attacker) or any(self._has_first_strike(b) for b in self.blockers):
            # First strike phase
            self._combat_phase(first_strike=True)

        # Normal damage phase (skip first strike creatures that already dealt damage)
        self._combat_phase(first_strike=False)

    def _combat_phase(self, first_strike: bool):
        """Resolves damage for a phase (first strike or normal)"""
        damage_assignments = []  # (source, amount, target)

        # --- No blockers ---
        if not self.blockers:
            if not first_strike:
                defender = flip(self.gs.turn_mgr.player_turn_idx)
                damage_assignments.append((self.attacker, self.attacker.power, defender))

        else:
            # --- Attacker → blocker ---
            a = self.attacker
            if self._phase_applicable(a, first_strike):
                if len(self.blockers) > 1 and a.rampage_amt:
                    multiplier = len(self.blockers) - 1
                    a.modifiers.append(PTMod(s=a, p_adj=a.rampage_amt * multiplier,
                                             t_adj=a.rampage_amt * multiplier, expires='EOT'))

                target = self.blockers[0]
                if self.gs.perm_querier.can_damage(target, a):
                    damage_assignments.append((a, a.power, target))

            # --- Blockers → attacker ---
            for blocker in self.blockers:
                if self._phase_applicable(blocker, first_strike):
                    if self.gs.perm_querier.can_damage(self.attacker, blocker):
                        damage_assignments.append((blocker, blocker.power, self.attacker))

        # --- apply damage ---
        for source, amount, target in damage_assignments:
            self.gs.apply_damage(source, amount, target, is_combat=True)

        # --- run SBAs ---
        self.gs.check_state_based_actions()

    def _phase_applicable(self, creature: GameCard, first_strike: bool) -> bool:
        """Returns True if this creature should deal damage in the current phase."""
        return first_strike is self._has_first_strike(creature)

    @staticmethod
    def _has_first_strike(creature: "GameCard") -> bool:
        return 'First Strike' in creature.props.keyword_abilities


class CombatManager:
    def __init__(self):
        self.combats: list[Combat] = []

    @property
    def attackers(self) -> list[GameCard | None]:
        return [com.attacker for com in self.combats]

    @property
    def blockers(self) -> list[GameCard | None]:
        return [b for com in self.combats for b in com.blockers]

    def create_combat(self, gs: GameState, c: GameCard) -> None:
        self.combats.append(Combat(gs, c))

    def get_combat(self, c: GameCard) -> Combat | None:
        for com in self.combats:
            if c is com.attacker or c in com.blockers:
                return com

    def get_combatants_against(self, c: GameCard) -> list[GameCard | None]:
        com = self.get_combat(c)
        if not com:
            return []
        if com.attacker is c:
            return [b for b in com.blockers]
        if c in com.blockers:
            return [com.attacker]

    def remove_from_combat(self, c: GameCard):
        """If attacker, delete that combat object, untap attacker; if blocker, remove blocker from the combat object"""
        for com in self.combats:
            if com.attacker is c:
                com.attacker.untap()
                self.combats.remove(com)
                return
            for blocker in com.blockers:
                if blocker is c:
                    com.blockers.remove(blocker)
                    return
