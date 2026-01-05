from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum, Enum, auto
from typing import TYPE_CHECKING, Callable, Optional, Union

from models.damage import PreventNextDamage
from phase_fsm import Phase
from utils import flip

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from card_filter import CardFilter
from models.modifiers import PTTemp, KWATemp

Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

@dataclass
class ActAbilitySpec:
    """Used to create the activated abilities for entire card universe"""
    class AllowedPlayerTurn(Enum):
        CASTER = auto()
        OPPONENT = auto()

    cost_mana: str
    cost_tap: bool
    target_filter: Callable[[GameState, GameCard], Target] | None
    effect: Callable[[GameState, GameCard, Target], None]
    allowed_phases: list[Phase] = field(default_factory=list)
    allowed_player_turn: list[AllowedPlayerTurn | None] = field(default_factory=list)
    max_activations_per_turn: int = 999


@dataclass
class ActivatedAbility:
    """A Target can be: GameCard, list[GameCard], int for one player, tuple[int, int] for two players, None"""
    class AllowedPlayerTurn(Enum):
        CASTER = auto()
        OPPONENT = auto()

    card: GameCard
    cost_mana: str
    cost_tap: bool
    target_filter: Callable[[GameState, GameCard], Target] | None
    effect: Callable[[GameState, GameCard, Target], None]
    allowed_phases: list[Phase] = field(default_factory=list)
    allowed_player_turn: list[AllowedPlayerTurn | None] = field(default_factory=list)
    allowed_p_id_turns: int | None = None
    activated_cnt_this_turn: int = 0
    max_activations_per_turn: int = 999

    def __post_init__(self):
        """allowed_p_id_turns need knowledge of the card's owner and is assigned here;
        if allowed_player_turns is [], then the ability should be permitted on both turns"""
        if self.allowed_player_turn == self.AllowedPlayerTurn.CASTER:
            self.allowed_p_id_turns = self.card.orig_owner_id
        if self.allowed_player_turn == self.AllowedPlayerTurn.OPPONENT:
            self.allowed_p_id_turns = flip(self.card.orig_owner_id)

    def can_activate(self, gs: GameState) -> bool:
        if self.cost_tap and self.card.is_tapped:
            print("A")
            return False
        if self.cost_mana and not gs.mana_pools[self.card.orig_owner_id].can_pay(self.cost_mana):
            print("B")
            return False
        if self.allowed_phases and gs.phase not in self.allowed_phases:
            print("C")
            return False
        if self.allowed_p_id_turns and self.card.orig_owner_id != self.allowed_p_id_turns:
            print("D")
            return False
        if self.activated_cnt_this_turn >= self.max_activations_per_turn:
            print("E")
            return False
        return True


TARGET_FUNCS = {
    'all_creatures_and_players': lambda gs, source: gs.card_filter.in_play().creatures().result() + [0, 1],
    'artifacts_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().result(),
    'black_in_play': lambda gs, source: gs.card_filter.in_play().black().result(),
    'blue_in_play': lambda gs, source: gs.card_filter.in_play().blue().result(),
    'green_in_play': lambda gs, source: gs.card_filter.in_play().green().result(),
    'red_in_play': lambda gs, source: gs.card_filter.in_play().red().result(),
    'white_in_play': lambda gs, source: gs.card_filter.in_play().white().result(),
}


# --- COMMON EFFECT FUNCS ---
def prevent_next_damage_func(amt: int = None):
    def _effect(gs, src, _):
        gs.damage_preventions.append(PreventNextDamage(src, amt))
    return _effect

def deal_damage_func(amt: int = None):
    def _effect(gs, source, target):
        gs.apply_damage(source, amt, target)
    return _effect

def pump_func(p_delta: int, t_delta: int):
    def _effect(gs, source, t: GameCard):
        t.modifiers.temps.append(PTTemp(p_delta, t_delta))
    return _effect

# --- CARD SPECIFIC FUNCS ---
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
    gs.mana_pools[source.orig_owner_id].add_floating('B')
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

ACTIVATED_ABILITY: dict[str, list[ActAbilitySpec]] = {
    'aladdins-ring':
        [ActAbilitySpec('', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(4))],
    'ali-baba':
        [ActAbilitySpec('R', True, lambda gs, _: CardFilter(gs).in_play().walls().result(), lambda gs, src, t: t.tap(gs))],
    'amulet-of-kroog':
        [ActAbilitySpec('2', True, TARGET_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
    'apprentice-wizard':
        [ActAbilitySpec('U', True, lambda gs, source: source.orig_owner_id, lambda gs, s, t: gs.mana_pools[s.orig_owner_id].add_floating('C', 3))],
    'blessing':
        [ActAbilitySpec('W', False, None, pump_func(1, 1))],
    'book-of-rass':
        [ActAbilitySpec('2', False, lambda gs, source: source.orig_owner_id, lambda gs, source, t: book_of_rass_pay_life_draw_card(gs, source, t))],
    'brainwash':
        [ActAbilitySpec('3', False, None, lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Attack')))],
    'brothers-of-fire':
        [ActAbilitySpec('', True, TARGET_FUNCS['all_creatures_and_players'], lambda gs, source, t: brothers_of_fire_deals_damage(gs, source, t))],
    'carrion-ants':
        [ActAbilitySpec('1', False, None, pump_func(1, 1))],
    'circle-of-protection-artifacts':
        [ActAbilitySpec('1', False, TARGET_FUNCS['artifacts_in_play'],  # would this include instants/sorceries?
                        lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-black':
        [ActAbilitySpec('1', False, TARGET_FUNCS['black_in_play'],  # would this include instants/sorceries?
                        lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-blue':
        [ActAbilitySpec('1', False, TARGET_FUNCS['blue_in_play'],  # would this include instants/sorceries?
                        lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-green':
        [ActAbilitySpec('1', False, TARGET_FUNCS['green_in_play'],  # would this include instants/sorceries?
                        lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-red':
        [ActAbilitySpec('1', False, TARGET_FUNCS['red_in_play'],  # would this include instants/sorceries?
                        lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-white':
        [ActAbilitySpec('1', False, TARGET_FUNCS['white_in_play'],  # would this include instants/sorceries?
                        lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'conservator':
        [ActAbilitySpec('3', True, None, lambda gs, src, _: gs.damage_preventions.append(
                        PreventNextDamage(src, remaining=2, target_player=src.orig_owner_id)))],
    'dragon-engine':
        [ActAbilitySpec('2', False, None, pump_func(1, 0))],
    'dwarven-demolition-team':
        [ActAbilitySpec('', True, lambda gs, source: CardFilter(gs).in_play().by_sub_type('Wall').result(),
                        lambda gs, source, t: gs.send_to_graveyard_from_play(t))],
    'electric-eel':
        [ActAbilitySpec('RR', False, None, lambda gs, s, t: electric_eel_pump_and_damage(gs, s, t))],
    'elves-of-deep-shadow':
        [ActAbilitySpec('', True, None, lambda gs, s, t: elves_of_deep_shadow_add_mana_but_damage(gs, s, t))],
    'emerald-dragonfly':
        [ActAbilitySpec('GG', False, None, lambda gs, s, t: t.modifiers.temps.append(KWATemp('add', 'First Strike')))],
    'exorcist':
        [ActAbilitySpec('1W', True, lambda gs, source: CardFilter(gs).in_play().creatures().black().result(),
                        lambda gs, source, t: gs.send_to_graveyard_from_play(t))],
    'farmstead':
        [ActAbilitySpec('WW', True, lambda gs, _: gs.player_turn_idx, lambda gs, _, t: gs.increment_life(gs.player_turn_idx, 1))],
    'fire-drake':
        [ActAbilitySpec('R', False, None, pump_func(1, 0), max_activations_per_turn=1)],
    'fire-sprites':
        [ActAbilitySpec('G', True, lambda _, s: s.orig_owner_id, lambda gs, s, t: gs.mana_pools[s.orig_owner_id].add_floating('R', 1))],
    'firebreathing':
        [ActAbilitySpec('R', False, None, pump_func(1, 0))],
    'flood':
        [ActAbilitySpec('UU', False, lambda gs, source: CardFilter(gs).in_play().creatures().tapped(False).has('Flying',False).result(),
                        lambda gs, source, t: t.tap(gs))],
    'flying-carpet':
        [ActAbilitySpec('2', True, lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                        lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Flying')))],
    'fountain-of-youth':
        [ActAbilitySpec('2', True, lambda _, s: s.orig_owner_id, lambda gs, s, _: gs.increment_life(s.orig_owner_id, 1, s))],
    'frozen-shade':
        [ActAbilitySpec('B', False, None, pump_func(1, 1))],
    'ghosts-of-the-damned':
        [ActAbilitySpec('', True, lambda gs, source: CardFilter(gs).in_play().creatures().result(), pump_func(-1, 0))],
    'goblin-balloon-brigade':
        [ActAbilitySpec('R', False, lambda gs, source: source,   # Is this the best way to do this?
                        lambda gs, _, t: t.modifiers.temps.append(KWATemp('add', 'Flying')))],
    'granite-gargoyle':
        [ActAbilitySpec('R', False, lambda gs, source: source,  pump_func(0, 1))],
    'grapeshot-catapult':
        [ActAbilitySpec('', True, lambda gs, _: CardFilter(gs).in_play().creatures().has('Flying').result(),
                        deal_damage_func(4))],
    'greed':
        [ActAbilitySpec('B', False, lambda _, s: s.orig_owner_id, lambda gs, s, t: greed_pay_life_draw_card(gs, s, t))],
    'hammerheim':
        # {T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn.
        [ActAbilitySpec('', True, lambda _, s: s.orig_owner_id, lambda gs, s, t: gs.mana_pools[s.orig_owner_id].add_floating('R', 1)),
         ActAbilitySpec('', True, lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                        lambda gs, source, t: hammerheim_remove_all_walks(gs, source, t))],
    'holy-armor':
        [ActAbilitySpec('W', False, None, lambda gs, source, t: t.modifiers.temps.append(PTTemp(0, 1)))],
    'hyperion-blacksmith':
        # {T}: You may tap or untap target artifact an opponent controls
        [ActAbilitySpec('', True, lambda gs, s: CardFilter(gs).on_player_board(flip(s.orig_owner_id)).artifacts().result(),
                        lambda gs, source, t: t.untap(gs) if t.is_tapped else t.tap(gs))],
    'icy-manipulator':
    # {1}, {T}: Tap target artifact, creature, or land
        [ActAbilitySpec('1', True, lambda gs, source: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).tapped(False).result(),
                        lambda gs, source, t: t.tap(gs))],
    'instill-energy':
        # {0}: Untap enchanted creature. Activate only during your turn and only once each turn
        [ActAbilitySpec('', False, None, lambda gs, source, t: t.untap(gs),
                        allowed_player_turn=[ActivatedAbility.AllowedPlayerTurn.CASTER], max_activations_per_turn=1)],
    'northern-paladin':
        [ActAbilitySpec('WW', True, lambda gs, source: CardFilter(gs).in_play().black().by_type(['Creature', 'Enchantment']).result(),
                        lambda gs, source, t: gs.send_to_graveyard_from_play(t))],
    'pirate-ship':
        [ActAbilitySpec('', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'prodigal-sorcerer':
        [ActAbilitySpec('', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'psionic-entity':
        [ActAbilitySpec('', True, TARGET_FUNCS['all_creatures_and_players'],
                        lambda gs, source, t: psionic_entity_deals_damage(gs, source, t))],
    'samite-healer':
        [ActAbilitySpec('', True, TARGET_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
    'wall-of-water':
        [ActAbilitySpec('U', False, None, pump_func(1, 0))]
}

def add_activated_abilities(cards: list[GameCard]) -> None:
    for c in cards:
        if specs := ACTIVATED_ABILITY.get(c.props.slug):
            for spec in specs:
                aa = ActivatedAbility(card=c, cost_mana=spec.cost_mana, cost_tap=spec.cost_tap,
                                      target_filter=spec.target_filter, effect=spec.effect,
                                      allowed_phases=spec.allowed_phases, allowed_player_turn=spec.allowed_player_turn,
                                      max_activations_per_turn=spec.max_activations_per_turn)
                c.abilities.append(aa)


# DON'T DELETE THIS UNTIL PRETTY HAPPY W THE NEWER ABOVE APPROACH
def add_activated_abilities_2(cards: list[GameCard]) -> None:
    for c in cards:
        # commenting this for now, as land is being auto-paid & tapped
        # if c.props.is_basic_land:
        #     color = BASIC_LAND_MANA_PRODUCED[c.props.slug]
        #     [ActAbilitySpec('', True, target_filter=None,
        #                        effect=lambda gs, source, _: gs.mana_pools[source.orig_owner_id].add(color)))
        if c.props.slug == 'aladdins-ring':
            # all creatures & players are targets
            c.abilities.append(ActivatedAbility(c, '', True,
                                                target_filter=TARGET_FUNCS['all_creatures_and_players'],
                                                effect=deal_damage_func(4)))
        if c.props.slug == 'ali-baba':
            c.abilities.append(ActivatedAbility(
                c, 'R', True, target_filter=lambda gs, source: CardFilter(gs).in_play().walls().result(),
                                  effect=lambda gs, source, t: t.tap(gs)))
        if c.props.slug == 'amulet-of-kroog':
            # same target_filter & effect as samite-healer
            c.abilities.append(ActivatedAbility(c, '2', True,
                                                target_filter=TARGET_FUNCS['all_creatures_and_players'],
                                                effect=prevent_next_damage_func(1)))
        if c.props.slug == 'apprentice-wizard':
            c.abilities.append(ActivatedAbility(c, 'U', True, target_filter=lambda gs, source: source.orig_owner_id,
                                                effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add_floating('C', 3)))
        if c.props.slug == 'blessing':
            c.abilities.append(ActivatedAbility(
                c, 'W', False, target_filter=None,
                effect=pump_func(1, 1)))
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
                               effect=pump_func(1, 1)))
        if c.props.slug == 'circle-of-protection-artifacts':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=TARGET_FUNCS['artifacts_in_play'],  # would this include instants/sorceries?
                                                effect=lambda gs, src, t: gs.damage_preventions.append(
                                                    PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id))))
        if c.props.slug == 'circle-of-protection-black':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=TARGET_FUNCS['black-in-play'],  # would this include instants/sorceries?
                                                effect=lambda gs, src, t: gs.damage_preventions.append(
                                                    PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id))))
        if c.props.slug == 'circle-of-protection-blue':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=TARGET_FUNCS['blue_in_play'],  # would this include instants/sorceries?
                                                effect=lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id))))
        if c.props.slug == 'circle-of-protection-green':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=TARGET_FUNCS['green_in_play'],  # would this include instants/sorceries?
                                                effect=lambda gs, src, t: gs.damage_preventions.append(
                                                    PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id))))
        if c.props.slug == 'circle-of-protection-red':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=TARGET_FUNCS['red-in-play'],  # would this include instants/sorceries?
                                                effect=lambda gs, src, t: gs.damage_preventions.append(
                                                    PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id))))
        if c.props.slug == 'circle-of-protection-white':
            c.abilities.append(ActivatedAbility(c, '1', False, target_filter=TARGET_FUNCS['white-in-play'],  # would this include instants/sorceries?
                                                effect=lambda gs, src, t: gs.damage_preventions.append(
                                                    PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id))))
        if c.props.slug == 'conservator':
            c.abilities.append(ActivatedAbility(c, '3', True,
                               effect=lambda gs, src, _: gs.damage_preventions.append(PreventNextDamage(src, remaining=2, target_player=src.orig_owner_id))))
        if c.props.slug == 'dragon-engine':
            c.abilities.append(ActivatedAbility(c, '2', False, target_filter=None,
                               effect=pump_func(1, 0)))
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
                               effect=pump_func(1, 0)))
        if c.props.slug == 'fire-sprites':
            c.abilities.append(ActivatedAbility(c, 'G', True, target_filter=lambda _, source: source.orig_owner_id,
                                                effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add_floating('R', 1)))
        if c.props.slug == 'firebreathing':
            c.abilities.append(ActivatedAbility(c, 'R', False, target_filter=None,
                               effect=pump_func(1, 0)))
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
                               effect=pump_func(1, 1)))
        if c.props.slug == 'ghosts-of-the-damned':
            c.abilities.append(ActivatedAbility(c, '', True,
                               lambda gs, source: CardFilter(gs).in_play().creatures().result(),
                               effect=pump_func(-1, 0)))
        if c.props.slug == 'goblin-balloon-brigade':
            c.abilities.append(ActivatedAbility(c, 'R', False,
                               target_filter=lambda gs, source: source,
                               effect=lambda gs, source, t: t.modifiers.temps.append(KWATemp('add', 'Flying'))))
        if c.props.slug == 'granite-gargoyle':
            c.abilities.append(ActivatedAbility(c, 'R', False, target_filter=lambda gs, source: source,  # Is this the best way to do this?
                               effect=pump_func(0, 1)))
        if c.props.slug == 'grapeshot-catapult':
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda gs, source: CardFilter(gs).in_play().creatures().has('Flying').result(),
                                                effect=deal_damage_func(4)))
        if c.props.slug == 'greed':
            c.abilities.append(ActivatedAbility(c, 'B', False, target_filter=lambda _, source: source.orig_owner_id,
                               effect=lambda gs, source, t: greed_pay_life_draw_card(gs, source, t)))
        if c.props.slug == 'hammerheim':
            # {T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn.
            c.abilities.append(ActivatedAbility(c, '', True, target_filter=lambda _, source: source.orig_owner_id,
                                                effect=lambda gs, _, t: gs.mana_pools[c.orig_owner_id].add_floating('R', 1)))
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
            c.abilities.append(ActivatedAbility(c, '', False, target_filter=None,
                                                effect=lambda gs, source, t: t.untap(gs),
                                                allowed_p_id_turns=[ActivatedAbility.AllowedPlayerTurn.CASTER],
                                                max_activations_per_turn=1))
        if c.props.slug == 'northern-paladin':
            c.abilities.append(ActivatedAbility(
                c, 'WW', True, target_filter=lambda gs, source: CardFilter(gs).in_play().black().by_type(['Creature', 'Enchantment']).result(),
                                  effect=lambda gs, source, t: gs.send_to_graveyard_from_play(t)))
        if c.props.slug in ('pirate-ship', 'prodigal-sorcerer'):
            # all creatures & players are targets
            c.abilities.append(ActivatedAbility(c, '', True,
                                                target_filter=TARGET_FUNCS['all_creatures_and_players'],
                                                effect=deal_damage_func(1)))
        if c.props.slug in ('psionic-entity'):
            # all creatures & players are targets
            c.abilities.append(ActivatedAbility(c, '', True,
                                                target_filter=TARGET_FUNCS['all_creatures_and_players'],
                                                effect=lambda gs, source, t: psionic_entity_deals_damage(gs, source, t)))
        if c.props.slug == 'samite-healer':
            # all creatures & players can be protected
            c.abilities.append(ActivatedAbility(c, '', True,
                                                target_filter=TARGET_FUNCS['all_creatures_and_players'],
                                                effect=prevent_next_damage_func(1)))
        if c.props.slug == 'wall-of-water':
            c.abilities.append(ActivatedAbility(c, 'U', False, target_filter=None,
                               effect=pump_func(1, 0)))


if __name__ == '__main__':
    ...
