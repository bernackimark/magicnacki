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
    killed_creatures: list[GameCard] = field(default_factory=list)

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

        # Clean up combat, move dead creatures to graveyard
        self._end_combat()

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
                    a.modifiers.items.append(
                        PTMod(s=a, p_adj=a.rampage_amt * multiplier,
                              t_adj=a.rampage_amt * multiplier, expires='EOT')
                    )

                target = self.blockers[0]
                if self.gs.query_mgr.can_damage(target, a):
                    damage_assignments.append((a, a.power, target))

            # --- Blockers → attacker ---
            for blocker in self.blockers:
                if self._phase_applicable(blocker, first_strike):
                    if self.gs.query_mgr.can_damage(self.attacker, blocker):
                        damage_assignments.append((blocker, blocker.power, self.attacker))

        # --- apply damage ---
        for source, amount, target in damage_assignments:
            self.gs.apply_damage(source, amount, target, is_combat=True)

        # --- run SBAs ---
        self.gs.check_state_based_actions()

    @staticmethod
    def _phase_applicable(creature: GameCard, first_strike: bool) -> bool:
        """Returns True if this creature should deal damage in the current phase."""
        has_fs = 'First Strike' in creature.props.keyword_abilities
        return first_strike == has_fs or not first_strike  # normal phase includes non-first strike

    @staticmethod
    def _has_first_strike(creature: "GameCard") -> bool:
        return 'First Strike' in creature.props.keyword_abilities

    def _end_combat(self):
        """Moves all creatures with lethal damage to the graveyard"""
        pass
        # # I don't think having "killed_creatures" is the best design; and cards dying happens upstream
        # # Attacker
        # if self.attacker.toughness - self.attacker.damage_received_this_turn <= 0:
        #     self.killed_creatures.append(self.attacker)
        #
        # # Blockers
        # for b in self.blockers:
        #     if b.toughness - b.damage_received_this_turn <= 0:
        #         if b not in self.killed_creatures:
        #             self.killed_creatures.append(b)
        #
        # # Send killed creatures to graveyard
        # for c in self.killed_creatures:
        #     print('BBB')
        #     self.gs.destroy(c)
        #     print('CCC')

    def get_combatants_against(self, c: GameCard) -> list[GameCard]:
        if self.attacker == c:
            return [b for b in self.blockers]
        if c in self.blockers:
            return [self.attacker]
