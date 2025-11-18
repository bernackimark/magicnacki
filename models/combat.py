from dataclasses import dataclass, field

from models.game_card import GameCard


@dataclass
class Combat:
    gs: "GameState"
    attacker: GameCard
    blockers: list[GameCard] = field(default_factory=list)
    killed_creatures: list[GameCard] = field(default_factory=list)

    def __repr__(self):
        return f'{self.attacker} attacking {self.blockers}'

    def handle_damage(self):
        self._handle_first_strike_damage()

    @staticmethod
    def _deal_damage(source: GameCard, target: GameCard):
        amt = source.power
        source.combat_damage_dealt += amt
        target.combat_damage_received += amt

    @staticmethod
    def _has_first_strike(creature: GameCard) -> bool:
        return 'First Strike' in creature.props.keyword_abilities

    def _any_blocker_has_first_strike(self) -> bool:
        return any(self._has_first_strike(b) for b in self.blockers)

    def _handle_first_strike_damage(self):
        attacker_has_first_strike = self._has_first_strike(self.attacker)
        any_blocker_has_first_strike = self._any_blocker_has_first_strike()

        # If no first strike anywhere, just do regular combat damage
        if not attacker_has_first_strike and not any_blocker_has_first_strike:
            self._handle_combat_damage()
            return

        # First-Strike Phase
        if not self.blockers:
            self._handle_no_blockers()
        else:
            if attacker_has_first_strike:
                self._deal_damage(self.attacker, self.blockers[0])
            for blocker in self.blockers:
                if self._has_first_strike(blocker):
                    self._deal_damage(blocker, self.attacker)
            self._end_combat()

            # Continue to normal combat if attacker is still alive
            self._handle_combat_damage()

    def _handle_combat_damage(self):
        if not self.blockers:
            self._handle_no_blockers()
            return

        # Attacker normal damage (only if attacker survived first strike)
        if not self._has_first_strike(self.attacker) and self.attacker not in self.killed_creatures:
            self._deal_damage(self.attacker, self.blockers[0])
            # TODO: this deals all damage to the first blocker

        # Blocker normal damage
        for blocker in self.blockers:
            if blocker not in self.killed_creatures:
                self._deal_damage(blocker, self.attacker)

        self._end_combat()

    def _end_combat(self):
        if self.attacker.toughness - self.attacker.combat_damage_received <= 0:
            self.killed_creatures.append(self.attacker)

        for blocker in self.blockers:
            if blocker.toughness - blocker.combat_damage_received <= 0:
                if blocker not in self.killed_creatures:
                    self.killed_creatures.append(blocker)

        for c in self.killed_creatures:
            self.gs.send_to_graveyard(c)

    def _handle_no_blockers(self):
        dmg = self.attacker.power
        defender = self.gs.turn.out_turn_player_idx
        print(f"{self.attacker} deals {dmg} damage to player #{defender}")
        self.gs.decrement_life(defender, dmg, self.attacker)
        self._end_combat()
