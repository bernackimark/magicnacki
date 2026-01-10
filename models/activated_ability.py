from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable, Optional, Union

from constants import COLOR_LETTERS_W_COLORLESS
from models.damage import PreventNextDamage, DamageEvent
from models.effects.on_end_step import nettling_imp_on_end_step
from phase_fsm import Phase
from utils import flip

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from card_filter import CardFilter
from models.modifiers import PTTemp, KWATemp
from models.effects.global_ import scarecrow_func

Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

@dataclass
class AAS:
    """Activated Ability Spec; used to create the activated abilities for entire card universe"""
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


# --- COMMON/COMPLEX TARGET FUNCS
def opp_creatures_who_could_have_attacked_but_didnt(gs: GameState, source: GameCard) -> list[GameCard | None]:
    """Returns creatures who: have 'Attack' in kwa, no summoning sickness, didn't go into combat"""
    attackers = gs.card_filter.attackers().result()
    return [c for c in gs.card_filter.on_player_board(flip(source.orig_owner_id)).creatures().result()
            if c not in attackers and not c.has_summoning_sickness and 'Attack' in c.keyword_abilities]

TARGET_FUNCS: [str, Callable[[GameState, GameCard], list[Target]]] = {
    'all_creatures_and_players': lambda gs, source: gs.card_filter.in_play().creatures().result() + [0, 1],
    'artifact_creatures_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().creatures().result(),
    'artifacts_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().result(),
    'attackers': lambda gs, s: gs.card_filter.attackers().result(),
    'auras_on_lands': lambda gs, s: [a for c in gs.card_filter.in_play().lands().result()
                                     for a in c.modifiers.auras if isinstance(a, GameCard)],
    'auras_on_owners_creatures': lambda gs, s: [a for c in gs.card_filter.on_player_board(s).creatures().result()
                                                for a in c.modifiers.auras if isinstance(a, GameCard)],
    'black_in_play': lambda gs, source: gs.card_filter.in_play().black().result(),
    'black_and_red_in_play': lambda gs, source: [gs.card_filter.in_play().black().result() +
                                                 gs.card_filter.in_play().red().result()],
    'black_creatures_in_play': lambda gs, s: gs.card_filter.in_play().creatures().black().result(),
    'blue_creatures_in_play': lambda gs, s: gs.card_filter.in_play().creatures().blue().result(),
    'blue_in_play': lambda gs, source: gs.card_filter.in_play().blue().result(),
    'card_owner': lambda gs, s: s.orig_owner_id,
    'creatures_in_play': lambda gs, source: gs.card_filter.in_play().creatures().result(),
    'creatures_in_play_w_forestwalk': lambda gs, s: gs.card_filter.in_play().has('Forestwalk').result(),
    'creatures_in_play_wo_forestwalk': lambda gs, s: gs.card_filter.in_play().has('Forestwalk', False).result(),
    'creatures_and_enchantments_in_play': lambda gs, s: gs.card_filter.in_play().by_type(['Creature',
                                                                                          'Enchantment']).result(),
    'fliers_in_play': lambda gs, _: gs.card_filter.in_play().creatures().has('Flying').result(),
    'green_in_play': lambda gs, source: gs.card_filter.in_play().green().result(),
    'one_one_creatures_in_play': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                                                if c.power == 1 and c.toughness == 1],
    'opp_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(flip(s.orig_owner_id)).creatures().result(),
    'opp_creatures_who_could_have_but_didnt_attack': lambda gs, s: opp_creatures_who_could_have_attacked_but_didnt(gs, s),
    'red_in_play': lambda gs, source: gs.card_filter.in_play().red().result(),
    'stone_giant': lambda gs, s: [c for c in gs.card_filter.on_player_board(s).creatures().result()
                                  if c.toughness < s.power],
    'tapped_creatures': lambda gs, source: gs.card_filter.in_play().creatures().tapped().result(),
    'tapped_lands': lambda gs, s: gs.card_filter.in_play().lands().tapped().result(),
    'unblocked_attackers': lambda gs, source: gs.card_filter.unblocked_attackers().result(),
    'untapped_artifacts_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().untapped().result(),
    'walls_in_play': lambda gs, s: gs.card_filter.in_play().walls().result(),
    'white_in_play': lambda gs, source: gs.card_filter.in_play().white().result(),
    'your_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(s.orig_owner_id).creatures().result(),
}

# --- NON-CARD-SPECIFIC COMMON/COMPLEX EFFECT FUNCS ---
def add_mana_func(color: str, amt: int = 1):
    if color not in COLOR_LETTERS_W_COLORLESS:
        raise ValueError(f"Color must be {COLOR_LETTERS_W_COLORLESS}")

    def _effect(gs, s, t: GameCard):
        gs.mana_pools[s.orig_owner_id].add_floating(color, amt)
    return _effect

def add_remove_kwa_temp(add_or_remove: str, kwa: str):
    if add_or_remove not in {'add', 'remove'}:
        raise ValueError("add_or_remove parameter must be either 'add' or 'remove'")

    def _effect(gs, src, t: Target):
        t.modifiers.temps.append(KWATemp(add_or_remove, kwa))
    return _effect

def deal_damage_func(amt: int = None):
    def _effect(gs, source, target):
        gs.apply_damage(source, amt, target)
    return _effect

def destroy_all_non_land_perms(gs: GameState, s: GameCard, t: Target):
    for c in gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Enchantment']).result():
        gs.send_to_graveyard_from_play(c)

def destroy_func(gs: GameState, _: GameCard, t: Target):
    gs.send_to_graveyard_from_play(t)

def prevent_next_damage_func(amt: int = None):
    def _effect(gs, src, _):
        gs.damage_preventions.append(PreventNextDamage(src, amt))
    return _effect

def pump_func(p_delta: int, t_delta: int):
    def _effect(gs, source, t: GameCard):
        t.modifiers.temps.append(PTTemp(p_delta, t_delta))
    return _effect

# --- CARD SPECIFIC COMPLEX FUNCS ---
def book_of_rass_func(gs: GameState, c: GameCard, _: Target):
    gs.decrement_life(c.orig_owner_id, 2, c)
    gs.draw(gs.hands[c.orig_owner_id], gs.decks[c.orig_owner_id].cards, 1)

def brothers_of_fire_func(gs: GameState, source: GameCard, t: Target):
    """1 damage to target; 1 damage to caster/owner"""
    gs.apply_damage(source, 1, t)
    gs.apply_damage(source, 1, source.orig_owner_id)

def electric_eel_func(gs: GameState, source: GameCard, _: Target):
    source.modifiers.temps.append(PTTemp(2, 0))
    gs.apply_damage(source, 1, source.orig_owner_id)

def elves_of_deep_shadow_func(gs: GameState, source: GameCard, _: Target):
    gs.mana_pools[source.orig_owner_id].add_floating('B')
    gs.apply_damage(source, 1, source.orig_owner_id)

def forcefield_func(gs: GameState, s: GameCard, t: Target):
    gs.damage_preventions.append(PreventNextDamage(s, source_card=t, target_player=s.orig_owner_id, combat_only=True))
    gs.apply_damage(t, 1, s.orig_owner_id, is_combat=True)

def greed_func(gs: GameState, source: GameCard, _: Target):
    gs.decrement_life(source.orig_owner_id, 2, source)
    gs.draw(gs.hands[source.orig_owner_id], gs.decks[source.orig_owner_id].cards, 1)

def hammerheim_func(gs: GameState, source: GameCard, t: Target):
    for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
        t.modifiers.temps.append(KWATemp('remove', f'{land}walk'))

def kry_shield_func(gs: GameState, s: GameCard, t: Target):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    gs.damage_preventions.append(PreventNextDamage(s, source_card=t))
    t.modifiers.temps.append(PTTemp(0, t.props.casting_weight))

def jade_monolith_func(gs: GameState, s: GameCard, t: Optional[GameCard] = None):
    """target = the GameCard being protected"""

    def redirect_damage(prevented: int):
        gs.apply_damage(t, prevented, t.orig_owner_id)

    gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, on_prevent=redirect_damage))

def maze_of_ith_func(gs: GameState, s: GameCard, t: Target):
    the_combat = [com for com in gs.combats if com.attacker == t]
    if not the_combat:
        return
    gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, combat_only=True))
    for b in the_combat[0].blockers:
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
    t.untap(gs)

def orcish_artillery_func(gs: GameState, s: GameCard, t: Target):
    """{T}: This creature deals 2 damage to any target and 3 damage to you"""
    gs.apply_damage(s, 2, t)
    gs.apply_damage(s, 3, s.orig_owner_id)

def psionic_entity_func(gs: "GameState", source: "GameCard", t: Target):
    # {T}: This creature deals 2 damage to any target and 3 damage to itself
    gs.apply_damage(source, 2, t)
    gs.apply_damage(source, 3, source)

def rakalite_func(gs: GameState, s: GameCard, _: Target):
    prevent_next_damage_func(1)
    gs.return_to_hand(s)

def rocket_launcher_func(gs: GameState, s: GameCard, t: Target):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step."""
    gs.apply_damage(s, 1, t)
    gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(s))

def shimian_nightstalker_func(gs: GameState, s: GameCard, t: Target):
    """{B}, {T}: All damage that would be dealt to you this turn by target attacking creature is dealt to this creature instead
    target = the GameCard doing the damage"""

    def redirect_damage(prevented: int):
        gs.apply_damage(t, prevented, t.orig_owner_id)

    gs.damage_preventions.append(PreventNextDamage(s, None, target_player=s.orig_owner_id,
                                                   source_card=t, on_prevent=redirect_damage))

def stone_giant_func(gs: GameState, s: GameCard, t: Target):
    """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
    Destroy that creature at the beginning of the next end step."""
    add_remove_kwa_temp('add', 'Flying')
    gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(t))


ACTIVATED_ABILITY: dict[str, list[AAS]] = {
    'aladdins-ring': [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(4))],
    'ali-baba': [AAS('R', True, TARGET_FUNCS['walls_in_play'], lambda gs, src, t: t.tap(gs))],
    'amulet-of-kroog': [AAS('2', True, TARGET_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
    'apprentice-wizard': [AAS('U', True, TARGET_FUNCS['card_owner'], add_mana_func('C', 3))],
    'argivian-blacksmith': [AAS('', True, TARGET_FUNCS['artifact_creatures_in_play'], prevent_next_damage_func(2))],
    'blessing': [AAS('W', False, None, pump_func(1, 1))],
    'book-of-rass': [AAS('2', False, TARGET_FUNCS['card_owner'], lambda gs, s, t: book_of_rass_func(gs, s, t))],
    'brainwash': [AAS('3', False, None, add_remove_kwa_temp('add', 'Attack'))],  # WARNING: double-check that this card is doing what's supposed to
    'brothers-of-fire':
        [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], lambda gs, s, t: brothers_of_fire_func(gs, s, t))],
    'carrion-ants': [AAS('1', False, None, pump_func(1, 1))],
    'circle-of-protection-artifacts':
        [AAS('1', False, TARGET_FUNCS['artifacts_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-black':
        [AAS('1', False, TARGET_FUNCS['black_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-blue':
        [AAS('1', False, TARGET_FUNCS['blue_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-green':
        [AAS('1', False, TARGET_FUNCS['green_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-red':
        [AAS('1', False, TARGET_FUNCS['red_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-white':
        [AAS('1', False, TARGET_FUNCS['white_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'conservator':
        [AAS('3', True, None, lambda gs, src, _: gs.damage_preventions.append(
                        PreventNextDamage(src, remaining=2, target_player=src.orig_owner_id)))],
    'dragon-engine': [AAS('2', False, None, pump_func(1, 0))],
    'dwarven-demolition-team': [AAS('', True, TARGET_FUNCS['walls_in_play'], destroy_func)],
    'electric-eel': [AAS('RR', False, None, lambda gs, s, t: electric_eel_func(gs, s, t))],
    'elves-of-deep-shadow': [AAS('', True, None, lambda gs, s, t: elves_of_deep_shadow_func(gs, s, t))],
    'emerald-dragonfly': [AAS('GG', False, None, add_remove_kwa_temp('add', 'First Strike'))],
    'exorcist': [AAS('1W', True, TARGET_FUNCS['black_creatures_in_play'], destroy_func)],
    'farmstead':
        [AAS('WW', True, lambda gs, _: gs.player_turn_idx, lambda gs, _, t: gs.increment_life(gs.player_turn_idx, 1))],
    'fire-drake': [AAS('R', False, None, pump_func(1, 0), max_activations_per_turn=1)],
    'fire-sprites': [AAS('G', True, lambda _, s: s.orig_owner_id, add_mana_func('R'))],
    'firebreathing': [AAS('R', False, None, pump_func(1, 0))],
    'flood':
        [AAS('UU', False, lambda gs, source: CardFilter(gs).in_play().creatures().untapped().has('Flying', False).result(),
             lambda gs, source, t: t.tap(gs))],
    'flying-carpet':
        [AAS('2', True, TARGET_FUNCS['creatures_in_play'], add_remove_kwa_temp('add', 'Flying'))],
    'forcefield':
        # Next time an unblocked creature of your choice would deal combat damage to you this turn, reduce damage to 1
        [AAS('1', False, TARGET_FUNCS['unblocked_attackers'], forcefield_func)],
    'fountain-of-youth':
        [AAS('2', True, lambda _, s: s.orig_owner_id, lambda gs, s, _: gs.increment_life(s.orig_owner_id, 1, s))],
    'frozen-shade': [AAS('B', False, None, pump_func(1, 1))],
    'ghosts-of-the-damned':
        [AAS('', True, TARGET_FUNCS['creatures_in_play'], pump_func(-1, 0))],
    'goblin-balloon-brigade':  # is lambda gs, source: source the best way?
        [AAS('R', False, lambda gs, source: source, add_remove_kwa_temp('add', 'Flying'))],
    'granite-gargoyle': [AAS('R', False, lambda gs, source: source, pump_func(0, 1))],
    'grapeshot-catapult': [AAS('', True, TARGET_FUNCS['fliers_in_play'], deal_damage_func(4))],
    'greater-realm-of-preservation':
        [AAS('1W', False, TARGET_FUNCS['black_and_red_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(
                            PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'greed': [AAS('B', False, TARGET_FUNCS['card_owner'], lambda gs, s, t: greed_func(gs, s, t))],
    'hammerheim':
        # {T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn.
        [AAS('', True, lambda _, s: s.orig_owner_id, add_mana_func('R')),
         AAS('', True, TARGET_FUNCS['creatures_in_play'], lambda gs, s, t: hammerheim_func(gs, s, t))],
    'holy-armor': [AAS('W', False, None, pump_func(0, 1))],
    'horn-of-deafening':
        [AAS('2', True, TARGET_FUNCS['creatures_in_play'],
             lambda gs, s, t: gs.damage_preventions.append(PreventNextDamage(s, source_card=t,
                                                                                        combat_only=True)))],
    'hyperion-blacksmith':
        # {T}: You may tap or untap target artifact an opponent controls
        [AAS('', True, lambda gs, s: CardFilter(gs).on_player_board(flip(s.orig_owner_id)).artifacts().result(),
             lambda gs, source, t: t.untap(gs) if t.is_tapped else t.tap(gs))],
    'icy-manipulator':
    # {1}, {T}: Tap target artifact, creature, or land
        [AAS('1', True, lambda gs, source: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).tapped(False).result(),
             lambda gs, source, t: t.tap(gs))],
    'instill-energy':
        # {0}: Untap enchanted creature. Activate only during your turn and only once each turn
        [AAS('', False, None, lambda gs, source, t: t.untap(gs),
             allowed_player_turn=[ActivatedAbility.AllowedPlayerTurn.CASTER], max_activations_per_turn=1)],
    'jade-monolith': [AAS('1', False, TARGET_FUNCS['all_creatures_and_players'], jade_monolith_func)],
    'jandors-saddlebags': [AAS('3', True, TARGET_FUNCS['tapped_creatures'], lambda gs, source, t: t.untap(gs))],
    'jayemdae-tome':
        [AAS('4', True, TARGET_FUNCS['card_owner'],
             lambda gs, s, t: gs.draw(gs.hands[s.orig_owner_id], gs.decks[s.orig_owner_id].cards, 1))],
    'killer-bees': [AAS('G', False, lambda gs, source: source, pump_func(1, 1))],
    'king-suleiman':
        [AAS('', True, lambda gs, s: gs.card_filter.in_play().by_sub_type(['Djinn', 'Efreet']).result(),
             destroy_func)],
    'kry-shield': [AAS('2', True, TARGET_FUNCS['your_creatures_in_play'], kry_shield_func)],
    'ley-druid':
        [AAS('', True, TARGET_FUNCS['tapped_lands'], lambda gs, source, t: t.untap(gs))],
    'llanowar-elves': [AAS('', True, TARGET_FUNCS['card_owner'], add_mana_func('G'))],
    'maze-of-ith': [AAS('', True, lambda gs, s: gs.card_filter.attackers().result(), maze_of_ith_func)],
    'merfolk-assassin':
        [AAS('', True, lambda gs, source: gs.card_filter.in_play().has('Islandwalk').result(), destroy_func)],
    'miracle-worker':
        [AAS('', True, TARGET_FUNCS['auras_on_owners_creatures'], destroy_func)],  # should i send an aura to the graveyard w/o using host.remove_aura()?
    'mox-emerald': [AAS('', True, TARGET_FUNCS['card_owner'], add_mana_func('G'))],
    'mox-jet': [AAS('', True, TARGET_FUNCS['card_owner'], add_mana_func('B'))],
    'mox-pearl': [AAS('', True, TARGET_FUNCS['card_owner'], add_mana_func('W'))],
    'mox-ruby': [AAS('', True, TARGET_FUNCS['card_owner'], add_mana_func('R'))],
    'mox-sapphire': [AAS('', True, TARGET_FUNCS['card_owner'], add_mana_func('U'))],
    'nettling-imp': [AAS('', True, TARGET_FUNCS['opp_creatures_who_could_have_but_didnt_attack'],
                         lambda gs, s, t: gs.end_step_funcs.append(nettling_imp_on_end_step),
                         allowed_player_turn=[ActivatedAbility.AllowedPlayerTurn.OPPONENT],
                         allowed_phases=[phase for phase in Phase if phase < Phase.DECLARE_ATTACKERS])],
    'nevinyrrals-disk': [AAS('1', True, None, lambda gs, s, t: destroy_all_non_land_perms(gs, s, t))],
    'northern-paladin': [AAS('WW', True, TARGET_FUNCS['creatures_and_enchantments_in_play'], destroy_func)],
    'oasis': [AAS('', True, TARGET_FUNCS['creatures_in_play'], prevent_next_damage_func(1))],
    'orcish-artillery': [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], orcish_artillery_func)],
    'pendelhaven':
        [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('G')),
         AAS('', True, TARGET_FUNCS['one_one_creatures_in_play'], pump_func(1, 2))],
    'pirate-ship': [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'pixie-queen':
        [AAS('GGG', True, TARGET_FUNCS['creatures_in_play'], add_remove_kwa_temp('add', 'Flying'))],
    'pradesh-gypsies': [AAS('1G', True, TARGET_FUNCS['creatures_in_play'], pump_func(-2, 0))],
    'prodigal-sorcerer': [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'psionic-entity':
        [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], lambda gs, s, t: psionic_entity_func(gs, s, t))],
    'radjan-spirit':
        [AAS('', True, TARGET_FUNCS['creatures_in_play'], add_remove_kwa_temp('remove', 'Flying'))],
    'rakalite': [AAS('2', False, TARGET_FUNCS['all_creatures_and_players'], rakalite_func)],
    'relic-barrier': [AAS('', True, TARGET_FUNCS['untapped_artifacts_in_play'], lambda gs, s, t: t.tap(gs))],
    'rod-of-ruin': [AAS('3', True, TARGET_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'rocket-launcher':
        [AAS('2', False, TARGET_FUNCS['all_creatures_and_players'], lambda gs, s, t: rocket_launcher_func(gs, s, t))],
    'royal-assassin': [AAS('', True, TARGET_FUNCS['tapped_creatures'], destroy_func)],
    'samite-healer': [AAS('', True, TARGET_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
    'savaen-elves': [AAS('GG', True, TARGET_FUNCS['auras_on_lands'], destroy_func)],
    'scarecrow': [AAS('6', True, None,
                      lambda gs, s, t: gs.global_effects.append((s, scarecrow_func)))],
    'scarwood-hag': [AAS('GGGG', True, TARGET_FUNCS['creatures_in_play_wo_forestwalk'],
                         add_remove_kwa_temp('add', 'Forestwalk')),
                     AAS('GGGG', True, TARGET_FUNCS['creatures_in_play_w_forestwalk'],
                         add_remove_kwa_temp('remove', 'Forestwalk'))],
    'shimian-night-stalker': [AAS('B', True, TARGET_FUNCS['attackers'], shimian_nightstalker_func)],
    'shivan-dragon': [AAS('R', False, None, pump_func(1, 0))],
    'sisters-of-the-flame': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('R'))],
    'sol-ring': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('C', 2))],
    'sorceress-queen': [AAS('', True, lambda gs, s: [c for c in TARGET_FUNCS['creatures_in_play'] if c != s],
                            lambda gs, s, t: t.modifiers.temps.append(PTTemp(-t.power, t.toughness - 2)))],
    'spinal-villain': [AAS('', True, TARGET_FUNCS['blue_creatures_in_play'], destroy_func)],
    'staff-of-zegon': [AAS('3', True, TARGET_FUNCS['creatures_in_play'], pump_func(-2, 0))],
    'stone-giant': [AAS('', True, TARGET_FUNCS['stone_giant'], stone_giant_func)],
    'wall-of-water': [AAS('U', False, None, pump_func(1, 0))]
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


if __name__ == '__main__':
    ...
