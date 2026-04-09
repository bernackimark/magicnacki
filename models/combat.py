from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.modifiers import PTMod

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard


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
        # If no blockers, attacker damage goes to defending player
        if not self.blockers:
            if not first_strike:  # only deal damage once, during normal phase
                defender = self.gs.turn.out_turn_player_idx
                self.gs.apply_damage(self.attacker, self.attacker.power, defender, is_combat=True)
            return

        # Attacker damage to blockers
        # Currently only assigns damage to the first blocker w no damage splitting across blockers
        # Trample logic is inside gs.apply_damage() cuz I need access to damage preventions (would prefer it's here)
        if self.attacker not in self.killed_creatures:
            a = self.attacker
            if self._phase_applicable(a, first_strike):
                print('ZZZ', len(self.blockers), a.rampage_amt)
                if len(self.blockers) > 1 and a.rampage_amt:
                    multiplier = len(self.blockers) - 1
                    a.modifiers.items.append(PTMod(s=a, p_adj=a.rampage_amt * multiplier,
                                                   t_adj=a.rampage_amt * multiplier, expires='EOT'))
                target = self.blockers[0]
                if self.gs.can_damage(target, a):
                    self.gs.apply_damage(a, a.power, target, is_combat=True)

        # Blocker damage to attacker
        for blocker in self.blockers:
            if blocker not in self.killed_creatures:
                if self._phase_applicable(blocker, first_strike):
                    if self.gs.can_damage(self.attacker, blocker):
                        self.gs.apply_damage(blocker, blocker.power, self.attacker, is_combat=True)

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
        # Attacker
        if self.attacker.toughness - self.attacker.damage_received_this_turn <= 0:
            self.killed_creatures.append(self.attacker)

        # Blockers
        for b in self.blockers:
            if b.toughness - b.damage_received_this_turn <= 0:
                if b not in self.killed_creatures:
                    self.killed_creatures.append(b)

        # Send killed creatures to graveyard
        for c in self.killed_creatures:
            self.gs.destroy(c)
