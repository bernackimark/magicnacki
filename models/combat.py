from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.events_all import StateBasedEvent
from models.modifiers import PTMod
from models.utils import flip
from models.zone import Zone

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
    _gs: GameState
    attacker: GameCard
    blockers: list[GameCard] = field(default_factory=list)

    def __repr__(self):
        return f"{self.attacker} attacking {self.blockers}"

    @property
    def contains_first_strike(self) -> bool:
        return any('First Strike' in self.attacker.keyword_abilities or
                   'First Strike' in b.keyword_abilities for b in self.blockers)

    @property
    def attacking_player(self) -> int:
        return self.attacker.owner_id

    @property
    def defending_player(self) -> int:
        return flip(self.attacker.owner_id)

    def handle_damage(self):
        """Main entry point for combat damage resolution. Handles first strike & normal damage & unblocked attackers.
        Currently, all attacker damage is assigned to the first blocker, no damage splitting supported yet"""
        if self.contains_first_strike:
            # First strike phase
            self._combat_phase(first_strike=True)

        # Normal damage phase (skip assigning damage by first strikers, who already dealt damage)
        self._combat_phase(first_strike=False)

    def _combat_phase(self, first_strike: bool):
        """Resolves damage for a phase (first strike or normal)"""
        damage_assignments = []  # (source, amount, target)

        # --- No blockers ---
        if not self.blockers:
            if not first_strike:
                damage_assignments.append((self.attacker, self.attacker.power, self.defending_player))

        else:
            # --- Attacker → blocker ---
            a = self.attacker
            if self._phase_applicable(a, first_strike):
                if len(self.blockers) > 1 and a.rampage_amt:
                    multiplier = len(self.blockers) - 1
                    a.modifiers.append(PTMod(s=a, p_adj=a.rampage_amt * multiplier,
                                             t_adj=a.rampage_amt * multiplier, expires='EOT'))

                target = self.blockers[0]
                # If blocker is not on the battlefield (destroyed/bounced), it will not receive a damage assignment
                if target.zone == Zone.BATTLEFIELD:
                    if self._gs.perm_querier.can_damage(target, a):
                        damage_assignments.append((a, a.power, target))

            # --- Blockers → attacker ---
            for blocker in self.blockers:
                if self._phase_applicable(blocker, first_strike):
                    if self._gs.perm_querier.can_damage(self.attacker, blocker):
                        damage_assignments.append((blocker, blocker.power, self.attacker))

        # --- apply damage ---
        for source, amount, target in damage_assignments:
            self._gs.apply_damage(source, amount, target, is_combat=True)

        # --- run SBAs ---
        self._gs.event_mgr.emit(StateBasedEvent())
        # self.gs.check_state_based_actions()

    @staticmethod
    def _phase_applicable(creature: GameCard, first_strike: bool) -> bool:
        """Returns True if this creature should deal damage in the current phase."""
        if not first_strike and 'First Strike' not in creature.keyword_abilities:
            return True
        if first_strike and 'First Strike' in creature.keyword_abilities:
            return True
        return False


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

    @property
    def has_a_first_strike_phase(self) -> bool:
        return any(c.contains_first_strike for c in self.combats)

    def create_combat(self, c: GameCard) -> None:
        self.combats.append(Combat(self._gs, c))

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
        """If attacker, delete that combat object, untap attacker;
        If a blocking creature is destroyed/bounced after it is declared as a blocker, the attacking creature remains
        blocked and will deal no damage, unless it has trample"""
        for com in self.combats:
            if com.attacker is c:
                com.attacker.untap()
                self.combats.remove(com)
                return
