from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum, Enum, auto
from typing import TYPE_CHECKING, Callable, Optional, Union

from models.damage import PreventNextDamage
from models.effects.activate import cop_blue_effect
from phase_fsm import Phase
from utils import flip

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from card_filter import CardFilter
from models.modifiers import PTTemp, KWATemp

Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

@dataclass
class ActivatedAbility:
    """A Target can be: GameCard, list[GameCard], int (single player's index), tuple[int, int] (both players' indices),
    None (I need review why this is needed by game_state.get_available_targets())
    """
    class AllowedPlayerTurn(Enum):
        CASTER = auto()
        OPPONENT = auto()

    card: "GameCard"
    cost_mana: str
    cost_tap: bool
    target_filter: Optional[Callable[[GameState, GameCard], Target]] = None
    effect: Callable[[GameState, GameCard, Target], None] = None
    allowed_phases: list[Phase] = field(default_factory=list)
    allowed_player_turns: list[AllowedPlayerTurn] = field(default_factory=list)
    activated_cnt_this_turn: int = 0
    max_activations_per_turn: int = 999

    def __post_init__(self):
        if not self.allowed_player_turns:
            self.allowed_player_turns = list(self.AllowedPlayerTurn)

    def _get_allowed_player_idx_turns(self) -> list[int]:
        allowed_p_idx_turns = []
        if self.AllowedPlayerTurn.CASTER in self.allowed_player_turns:
            allowed_p_idx_turns.append(self.card.orig_owner_id)
        if self.AllowedPlayerTurn.OPPONENT in self.allowed_player_turns:
            allowed_p_idx_turns.append(flip(self.card.orig_owner_id))
        return allowed_p_idx_turns

    def can_activate(self, gs: "GameState") -> bool:
        if self.cost_tap and self.card.is_tapped:
            return False
        if self.cost_mana and not gs.mana_pools[self.card.orig_owner_id].can_pay(self.cost_mana):
            return False
        if self.allowed_phases and gs.phase not in self.allowed_phases:
            return False
        if self.card.orig_owner_id not in self._get_allowed_player_idx_turns():
            return False
        if self.activated_cnt_this_turn >= self.max_activations_per_turn:
            return False
        return True

def book_of_rass_pay_life_draw_card(gs: GameState, c: GameCard, _: Target):
    gs.decrement_life(c.orig_owner_id, 2, c)
    gs.draw(gs.hands[c.orig_owner_id], gs.decks[c.orig_owner_id].cards, 1)

def brothers_of_fire_deals_damage(gs: GameState, source: GameCard, t: Target):
    """1 damage to target; 1 damage to caster/owner"""
    gs.apply_damage(source, 1, t)
    gs.apply_damage(source, 1, source.orig_owner_id)

def electric_eel_pump_and_damage(gs: GameState, source: GameCard, _: Target):
    source.modifiers.temps.append(PTTemp(2, 0))
    gs.apply_damage(source, 1, source.orig_owner_id)

def elves_of_deep_shadow_add_mana_but_damage(gs: GameState, source: GameCard, _: Target):
    gs.mana_pools[source.orig_owner_id].add('B')
    gs.apply_damage(source, 1, source.orig_owner_id)

def greed_pay_life_draw_card(gs: GameState, source: GameCard, _: Target):
    gs.decrement_life(source.orig_owner_id, 2, source)
    gs.draw(gs.hands[source.orig_owner_id], gs.decks[source.orig_owner_id].cards, 1)

def hammerheim_remove_all_walks(gs: GameState, source: GameCard, t: Target):
    for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
        t.modifiers.temps.append(KWATemp('remove', f'{land}walk'))

def psionic_entity_deals_damage(gs: "GameState", source: "GameCard", t: Target):
    # {T}: This creature deals 2 damage to any target and 3 damage to itself
    gs.apply_damage(source, 2, t)
    gs.apply_damage(source, 3, source)

def add_activated_abilities(cards: list[GameCard]) -> None:
    for c in cards:
        if c.props.slug == 'aladdins-ring':
            # damage to card
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: gs.apply_damage(source, 4, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, source, t: gs.apply_damage(source, 4, t)))
        if c.props.slug == 'ali-baba':
            c.abilities.append(ActivatedAbility(
                c, 'R', True, target_filter=lambda gs, source: CardFilter(gs).in_play().walls().result(),
                                  effect=lambda gs, source, t: t.tap(gs)))
        if c.props.slug == 'apprentice-wizard':
            c.abilities.append(ActivatedAbility(c, 'U', True, target_filter=lambda gs, source: source.orig_owner_id,
                               effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add('C', 3)))
        if c.props.slug == 'blessing':
            c.abilities.append(ActivatedAbility(
                c, 'W', False, target_filter=None,
                effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 1))))
        if c.props.slug == 'book-of-rass':
            c.abilities.append(ActivatedAbility(c, '2', False, target_filter=lambda gs, source: source.orig_owner_id,
                               effect=lambda gs, source, t: book_of_rass_pay_life_draw_card(gs, source, t)))
        if c.props.slug == 'brainwash':
            c.abilities.append(ActivatedAbility(c, '3', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Attack'))))
        if c.props.slug == 'brothers-of-fire':
            # damage to card
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: brothers_of_fire_deals_damage(gs, source, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, source, p_id: brothers_of_fire_deals_damage(gs, source, p_id)))
        if c.props.slug == 'carrion-ants':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 1))))
        if c.props.slug == 'circle-of-protection-blue':
            c.abilities.append(ActivatedAbility(c, '2', False, target_filter=lambda gs, source: CardFilter(gs).blue().result(),
                               effect=lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(source_filter=lambda dmg_src: dmg_src is t, target_player=src.orig_owner_id))))
        if c.props.slug == 'dragon-engine':
            c.abilities.append(ActivatedAbility(c, '2', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 0))))
        if c.props.slug == 'dwarven-demolition-team':
            c.abilities.append(ActivatedAbility(
                c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().by_sub_type('Wall').result(),
                                  effect=lambda gs, source, t: gs.send_to_graveyard_from_play(t)))
        if c.props.slug == 'electric-eel':
            c.abilities.append(ActivatedAbility(c, 'RR', False, target_filter=None,
                               effect=lambda gs, s, t: electric_eel_pump_and_damage(gs, s, t)))
        if c.props.slug == 'elves-of-deep-shadow':
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=None,
                               effect=lambda gs, s, t: elves_of_deep_shadow_add_mana_but_damage(gs, s, t)))
        if c.props.slug == 'emerald-dragonfly':
            c.abilities.append(ActivatedAbility(c, 'GG', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'First Strike'))))
        if c.props.slug == 'exorcist':
            c.abilities.append(ActivatedAbility(
                c, '1W', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().black().result(),
                                  effect=lambda gs, source, t: gs.send_to_graveyard_from_play(t)))
        if c.props.slug == 'farmstead':
            c.abilities.append(ActivatedAbility(c, 'WW', True, target_filter=lambda gs, _: gs.player_turn_idx,
                               effect=lambda gs, _, t: gs.increment_life(gs.player_turn_idx, 1)))
        if c.props.slug == 'fire-drake':
            c.abilities.append(ActivatedAbility(c, 'R', False, target_filter=None, max_activations_per_turn=1,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 0))))
        if c.props.slug == 'fire-sprites':
            c.abilities.append(ActivatedAbility(c, 'G', True, target_filter=lambda _, source: source.orig_owner_id,
                               effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add('R', 1)))
        if c.props.slug == 'firebreathing':
            c.abilities.append(ActivatedAbility(c, 'R', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 0))))
        if c.props.slug == 'flood':
            c.abilities.append(ActivatedAbility(
                c, 'UU', False, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().tapped(False).has('Flying', False).result(),
                                  effect=lambda gs, source, t: t.tap(gs)))
        if c.props.slug == 'flying-carpet':
            c.abilities.append(ActivatedAbility(c, '2', True,
                               target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Flying'))))
        if c.props.slug == 'fountain-of-youth':
            c.abilities.append(ActivatedAbility(c, '2', True, target_filter=lambda _, source: source.orig_owner_id,
                               effect=lambda gs, source, _: gs.increment_life(source.orig_owner_id, 1, c)))
        if c.props.slug == 'frozen-shade':
            c.abilities.append(ActivatedAbility(c, 'B', False, target_filter=lambda gs, source: source,  # Is this the best way to do this?
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 1))))
        if c.props.slug == 'ghosts-of-the-damned':
            c.abilities.append(ActivatedAbility(c, '', True,
                               lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(-1, 0))))
        if c.props.slug == 'goblin-balloon-brigade':
            c.abilities.append(ActivatedAbility(c, 'R', False,
                               target_filter=lambda gs, source: source,
                               effect=lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Flying'))))
        if c.props.slug == 'granite-gargoyle':
            c.abilities.append(ActivatedAbility(c, 'R', False, target_filter=lambda gs, source: source,  # Is this the best way to do this?
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(0, 1))))
        if c.props.slug == 'grapeshot-catapult':
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().has('Flying').result(),
                               effect=lambda gs, source, t: gs.apply_damage(source, 4, t)))
        if c.props.slug == 'greed':
            c.abilities.append(ActivatedAbility(c, 'B', False, target_filter=lambda _, source: source.orig_owner_id,
                               effect=lambda gs, source, t: greed_pay_life_draw_card(gs, source, t)))
        if c.props.slug == 'hammerheim':
            # {T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn.
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda _, source: source.orig_owner_id,
                               effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add('R', 1)))
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: hammerheim_remove_all_walks(gs, source, t)))
        if c.props.slug == 'holy-armor':
            c.abilities.append(ActivatedAbility(c, 'W', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(0, 1))))
        if c.props.slug == 'hyperion-blacksmith':
            # {T}: You may tap or untap target artifact an opponent controls.
            c.abilities.append(ActivatedAbility(c, '', True,
                               target_filter=lambda gs, source: CardFilter(gs).on_player_board(flip(c.orig_owner_id)).artifacts().result(),
                               effect=lambda gs, source, t: t.untap(gs) if t.is_tapped else t.tap(gs)))
        if c.props.slug == 'icy-manipulator':
            # {1}, {T}: Tap target artifact, creature, or land.
            c.abilities.append(ActivatedAbility(c, '1', True,
                               target_filter=lambda gs, source: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).tapped(False).result(),
                               effect=lambda gs, source, t: t.tap(gs)))
        if c.props.slug == 'instill-energy':
            # {0}: Untap enchanted creature. Activate only during your turn and only once each turn.
            c.abilities.append(ActivatedAbility(c, '', False,  target_filter=None,
                               effect=lambda gs, source, t: t.untap(gs),
                               allowed_player_turns=[ActivatedAbility.AllowedPlayerTurn.CASTER],
                               max_activations_per_turn=1))
        if c.props.slug == 'northern-paladin':
            c.abilities.append(ActivatedAbility(
                c, 'WW', True, target_filter=lambda gs, source: CardFilter(gs).in_play().black().by_type(['Creature', 'Enchantment']).result(),
                                  effect=lambda gs, source, t: gs.send_to_graveyard_from_play(t)))
        if c.props.slug in ('pirate-ship', 'prodigal-sorcerer'):
            # damage to card
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: gs.apply_damage(source, 1, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, source, t: gs.apply_damage(source, 1, t)))
        if c.props.slug in ('psionic-entity'):
            # damage to card
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=lambda gs, source, t: psionic_entity_deals_damage(gs, source, t)))
            # damage to player
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, _: (0, 1),
                               effect=lambda gs, source, p_id: psionic_entity_deals_damage(gs, source, p_id)))
        if c.props.slug == 'wall-of-water':
            c.abilities.append(ActivatedAbility(c, 'U', False, target_filter=None,
                               effect=lambda gs, source, t: t.modifiers.temps.append(PTTemp(1, 0))))


if __name__ == '__main__':
    ...
