from dataclasses import dataclass, field

from build_deck import GameCard


@dataclass
class CombatDamage:
    damage_dealer: GameCard
    damage_receiver: GameCard
    amt: int

    def __post_init__(self):
        self.damage_dealer.power -= self.amt
        self.damage_receiver.toughness -= self.amt

    def __repr__(self):
        return f"Combat Damage: ID#{self.damage_dealer.owner_and_id} {self.damage_dealer} deals {self.amt} damage to creature ID#{self.damage_receiver.owner_and_id} {self.damage_receiver}"


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

    def _handle_first_strike_damage(self):
        if 'First Strike' not in self.attacker.props.keyword_abilities and \
                'First Strike' not in [kwa for b in self.blockers for kwa in b.props.keyword_abilities]:
            self._handle_combat_damage()
        else:
            if not self.blockers:
                self._handle_no_blockers()
            else:
                if 'First Strike' in self.attacker.props.keyword_abilities:
                    # TODO: this is hard-coded to assign damage to the first blocker
                    combat_damage = CombatDamage(self.attacker, self.blockers[0], self.attacker.power)
                    self.gs.effects.append(combat_damage.__repr__())
                for blocker in self.blockers:
                    if 'First Strike' in blocker.props.keyword_abilities:
                        combat_damage = CombatDamage(blocker, self.attacker, blocker.power)
                        self.gs.effects.append(combat_damage.__repr__())
                self._end_combat(self.gs)
                self._handle_combat_damage()

    def _handle_combat_damage(self):
        # TODO: this is hard-coded to assign damage to the first blocker
        if not self.blockers:
            self._handle_no_blockers()
        else:
            if 'First Strike' not in self.attacker.props.keyword_abilities and self.attacker not in self.killed_creatures:
                combat_damage = CombatDamage(self.attacker, self.blockers[0], self.attacker.power)
                self.gs.effects.append(combat_damage.__repr__())
            for blocker in self.blockers:
                if 'First Strike' not in self.attacker.props.keyword_abilities and blocker not in self.killed_creatures:
                    combat_damage = CombatDamage(blocker, self.attacker, blocker.power)
                    self.gs.effects.append(combat_damage.__repr__())
            self._end_combat(self.gs)

    def _end_combat(self, gs: "GameState"):
        if self.attacker.toughness <= 0:
            self.killed_creatures.append(self.attacker)
        for blocker in self.blockers:
            if blocker.toughness <= 0:
                if blocker not in self.killed_creatures:
                    self.killed_creatures.append(blocker)

        for c in self.killed_creatures:
            gs.send_to_graveyard(c)

    def _handle_no_blockers(self):
        print(f"{self.attacker} deals {self.attacker.power} damage to player #{self.gs.turn.out_turn_player_idx}")
        self.gs.decrement_life(self.gs.turn.out_turn_player_idx, self.attacker.power)
        self._end_combat(self.gs)
        return
