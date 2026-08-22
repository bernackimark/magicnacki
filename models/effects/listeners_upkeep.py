from __future__ import annotations

import random
from collections import defaultdict
from itertools import combinations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO, copy_card
from models.constants import KW, Zone
from models.game_card.counter_tokens import PUPA, PLUS_ONE, WIND, HUNGER, DREAM, VITALITY
from models.effects.base import Listener
from models.effects.resolvers_generic import Steal, BasePT
from models.events_all import UpkeepEvent, Event, StateBasedEvent
from models.game_card.modifiers import KWAMod, BasePTMod, PTMod
from models.systems.phase import Phase
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class BlackVise(Listener):
    """As opponent's upkeep, this artifact deals X damage to that player, X is = cards in their hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.pile_mgr.hands[opp_id])
        if opp_hand_len > 4:
            gs.apply_damage(s, opp_hand_len - 4, opp_id)

class CocoonUpkeep(Listener):
    """At your upkeep, remove a pupa counter from this Aura.
        If you can't, sac it, put a +1/+1 counter on enchanted creature, and that creature gains flying."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        p_id = gs.player_turn_idx
        host = source.host
        if p_id != source.owner_id:
            return
        if source.counters.get_count(PUPA):
            source.counters.remove_counter(PUPA)
            return
        gs.pile_mgr.destroy(source)
        host.counters.add_counter(PLUS_ONE)
        host.modifiers.append(KWAMod(s=source, item=KW.FLYING))

class CosmicHorror(Listener):
    """At your upkeep, destroy unless you pay {3BBB}. If destroyed this way, it deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        if not gs.mana_pools[source.owner_id].can_pay('3BBB'):
            gs.pile_mgr.destroy(source)
            gs.apply_damage(source, 7, source.owner_id)
            return
        options = [CO(f'Destroy {source}', lambda: self.destroy_and_damage(gs, source, 7)),
                   CO(f"Pay {{{'3BB'}}}", lambda: gs.pile_mgr.destroy(source))]
        # options = [DestroyAction(event.active_player, gs, source, source, False),
        #            PayMana(event.active_player, gs, source, '3BBB')]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def destroy_and_damage(gs: GameState, source: GameCard, damage_amt: int):
        gs.pile_mgr.destroy(source)
        gs.apply_damage(source, damage_amt, source.owner_id)

class CurseArtifact(Listener):
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        host = source.host
        host_owner = host.owner_id
        if not host or gs.player_turn_idx != host_owner:
            return
        options = [CO(f"Deal 2 damage to P#{host_owner}", lambda: gs.apply_damage(source, 2, host_owner)),
                   CO(f"Sac {host.props.name}", lambda: gs.pile_mgr.sacrifice(host))]
        gs.queue_choice(ChoiceAction(options))

class Cyclone(Listener):
    """At your upkeep, add a wind counter, then pay {G} for each wind counter on it or sac.
    If you pay, Cyclone deals damage = its wind counters to each creature and each player."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(WIND)
        wind_counters = source.counters.get_count(WIND)

        if not gs.mana_pools[source.owner_id].can_pay('G' * source.counters.get_count(WIND)):
            gs.pile_mgr.sacrifice(source)
            return

        options = [CO(f'Pay {wind_counters} G to deal {wind_counters} damage to all creatures & players',
                      lambda: self.pay_and_damage(gs, source, wind_counters)),
                   CO(f'Sac {source}', lambda: gs.pile_mgr.sacrifice(source))]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def pay_and_damage(gs: GameState, source: GameCard, wind_counters: int):
        gs.mana_pools[source.owner_id].pay('G' * wind_counters)

        for creature in list(gs.card_filter.in_play().creatures().result()):
            gs.apply_damage(source, wind_counters, creature)

        for p_id in range(2):
            gs.apply_damage(source, wind_counters, p_id)

        # options = [CyclonePayManaPerCounterDealDamage(source.owner_id, gs, source), Sac(source.owner_id, gs, source)]
        # gs.queue_choice(ChoiceAction(options))

class DemonicHordesUpkeep(Listener):
    """... At your upkeep, pay {BBB} or tap this creature and sacrifice a land of an opponent's choice"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            source.tap()
        elif len(your_lands) == 1:
            source.tap()
            gs.pile_mgr.destroy(your_lands[0])
        elif not gs.mana_pools[source.owner_id].can_pay('BBB'):
            source.tap()
            gs.action_on_idx = flip(source.owner_id)
            options = [CO(f"Sac opponent's {c}", lambda: gs.pile_mgr.sacrifice(c)) for c in your_lands]
            gs.queue_choice(ChoiceAction(options))
        else:
            options = [CO(f"Pay {{{'BBB'}}}", lambda: gs.mana_pools[source.owner_id].pay('BBB'))]
            # TODO:
            #  Get the opponent to select a land to sac
            #  these are its options in the existing AllowOpponentToDestroyALand
            #          options = [DestroyAction(flip(self.player_idx), self.gs, self.source, land)
            #                    for land in self.gs.card_filter.lands().on_player_board(self.player_idx).result()]

            gs.queue_choice(ChoiceAction(options))

class DropOfHoney(Listener):
    """At your upkeep, destroy the creature with the least power. It can't be regenerated.
    If two or more creatures are tied for least power, you choose one. When there are no creatures on the battlefield,
    sac Drop of Honey."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.player_turn_idx != source.owner_id:
            return
        creatures = gs.card_filter.creatures().in_play().result()
        if not creatures:
            gs.pile_mgr.destroy(source, allow_regeneration=False)
            return

        min_power = min([c.power for c in creatures])
        creatures_w_min_power = [c for c in creatures if c.power == min_power]

        if len(creatures_w_min_power) == 1:
            gs.pile_mgr.destroy(creatures_w_min_power[0], allow_regeneration=False)
            return

        # options = [DestroyAction(source.owner_id, gs, source, c, allow_regen=False) for c in creatures_w_min_power]
        options = [CO(f"Destroy {c}", lambda: gs.pile_mgr.destroy(c, False)) for c in creatures_w_min_power]
        gs.queue_choice(ChoiceAction(options))

class ElderSpawnUpkeep(Listener):
    """At YOUR upkeep, sac an Island or sac ES & it deals 6 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        your_islands = gs.card_filter.on_player_board(s.owner_id).islands().result()
        if not your_islands:
            gs.pile_mgr.sacrifice(s)
            gs.apply_damage(s, 6, s.owner_id)
            return

        options = [CO(f'Sac {i}', lambda: gs.pile_mgr.sacrifice(i)) for i in your_islands] + \
                  [CO(f'Sac {s} & it deals 6 damage to you', lambda: self.sac_w_damage(gs, s, 6))]
        # options = [Sac(s.owner_id, gs, island) for island in your_islands] + [Sac(s.owner_id, gs, s, 6)]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def sac_w_damage(gs: GameState, card: GameCard, damage_amt: int):
        gs.pile_mgr.sacrifice(card)
        gs.apply_damage(card, damage_amt, card.owner_id)

class EnergyFlux(Listener):
    """All artifacts have 'At your [the owner's] upkeep, sacrifice this artifact unless you pay {2}'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_artifact in gs.card_filter.on_player_board(event.active_player).artifacts().result():
            if not gs.mana_pools[event.active_player].can_pay('2'):
                gs.pile_mgr.sacrifice(your_artifact)
            options = [CO(f"Pay {{{'2'}}}", lambda: gs.mana_pools[source.owner_id].pay('2')),
                       CO(f"Sac {source}", lambda: gs.pile_mgr.sacrifice(source))]
            # options = [PayMana(event.active_player, gs, source, '2'), Sac(event.active_player, gs, source)]
            gs.queue_choice(ChoiceAction(options))

class ErhnamDjinn(Listener):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        targets = gs.card_filter.on_player_board(flip(s.owner_id)).non_wall_creatures().result()
        if not targets:
            return
        if len(targets) == 1:
            targets[0].modifiers.append(KWAMod(item=KW.FORESTWALK, s=s, expires='EOT'))
            return
        kwa_mod = KWAMod(s=s, item='Forestwalk')
        options = [CO(f'Give Forestwalk to {t}', lambda: t.modifiers.append(kwa_mod)) for t in targets]
        # options = [AddKWA(s.owner_id, gs, s, t, KW.FORESTWALK) for t in targets]
        gs.queue_choice(ChoiceAction(options))

class ErosionUpkeep(Listener):
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or event.active_player != source.host.owner_id:
            return
        host_owner = source.host.owner_id
        options = []
        if gs.mana_pools[host_owner].can_pay('1'):
            options.append(CO(f"Pay {{{'1'}}}", lambda: gs.mana_pools[host_owner].pay('1')))
        options.append(CO(f"Pay 1 life", lambda: gs.score_mgr.decrement_life(host_owner, 1, source, gs)))
        options.append(CO(f"Destroy {source.host}", lambda: gs.pile_mgr.destroy(source.host)))

        gs.queue_choice(ChoiceAction(options))

class Fasting(Listener):
    """At your upkeep, add a hunger counter. Destroy Fasting if >=5 hunger counters.
    If you would begin your draw step, you may skip that step instead. If you do, you gain 2 life ..."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(HUNGER)
        if source.counters.get_count(HUNGER) > 4:
            gs.pile_mgr.destroy(source)
        options = [CO('Skip Draw Phase & Gain 2 life', lambda: self.skip_draw_phase_gain_life(gs, source.owner_id, 2))]
        # options = [SkipDrawPhaseGainLife(source.owner_id, gs, 2)]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def skip_draw_phase_gain_life(gs: GameState, p_id: int, amt: int):
        gs.phase_mgr.set_phase(Phase.MAIN)
        gs.score_mgr.increment_life(p_id, amt, source=None, gs=gs)

class ForceOfNatureUpkeep(Listener):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        if not gs.mana_pools[s.owner_id].can_pay('GGGG'):
            gs.apply_damage(s, 8, s.owner_id)
            return
        options = [CO(f"Pay {{{'GGGG'}}}", lambda: gs.mana_pools[s.owner_id].pay('GGGG')),
                   CO(f"{s} deals 8 damage to you", lambda: gs.apply_damage(s, 8, s.owner_id))]
        gs.queue_choice(ChoiceAction(options))

class GabrielAngelfire(Listener):
    """At your upkeep, choose flying, first strike, trample, rampage 3. GA gains that ability until your next upkeep."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        kwa_options = (KW.FLYING, KW.FIRST_STRIKE, KW.TRAMPLE, KW.RAMPAGE_3)
        options = [CO(f'{s} gains {o}', lambda: s.modifiers.append(KWAMod(s=s, item=o))) for o in kwa_options]
        gs.queue_choice(ChoiceAction(options))

class GhazbanOgre(Listener):
    """At your upkeep, if a player has more life than each other player,
    the player with the most life gains control of this creature (assuming "your" = the current controller)"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: Event):
        if gs.player_turn_idx != source.owner_id:
            return
        if len(set(gs.life)) == 1:
            return
        most_life_player_idx = max(range(len(gs.life)), key=lambda i: gs.life[i])
        if most_life_player_idx != source.owner_id:
            Steal().resolve(gs, source, source)

class GiantSlugUpkeep(Listener):
    """At your next upkeep, GS gains landwalk of your choice until the end of that turn."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        kwa_options = (KW.FORESTWALK, KW.ISLANDWALK, KW.ISLANDWALK, KW.PLAINSWALK, KW.SWAMPWALK)
        options = [CO(f'{s} gains {o}', lambda: s.modifiers.append(KWAMod(s=s, item=o))) for o in kwa_options]
        gs.queue_choice(ChoiceAction(options))

class Halfdane(Listener):
    """H's base PT = (3, 3)
    At your upkeep, change H's base PT = PT of target creature other than H until end of your NEXT upkeep
    If no legal targets, H's base PT = (3, 3)"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return

        if existing_mod := next((mod for mod in s.modifiers.get(BasePTMod) if mod.s is s), None):
            s.modifiers.remove(existing_mod)

        targets = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not targets:
            s.base_pt = (3, 3)
        if len(targets) == 1:
            target = targets[0]
            s.modifiers.append(BasePT(target.power, target.toughness))
            return
        options = [CO(f"Change {s}'s base PT to that of {target}",
                      lambda t=target: BasePT(t.power, t.toughness).resolve(gs, s, s)) for target in targets]
        gs.queue_choice(ChoiceAction(options))

class HazezonTamarTokenCreation(Listener):
    """Create X 1/1 Sand Warrior tokens at your next upkeep; X is the number of lands you control at that time"""
    listens_to = UpkeepEvent

    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.player_turn_idx != source.owner_id:
            return

        from .resolvers_generic import CreateTokenCreature
        for _ in gs.card_filter.lands().on_player_board(self.owner_id).result():
            CreateTokenCreature('sand-warrior').resolve(gs, source)

        gs.event_mgr.unregister_specific_effect(self)


class IvoryTower(Listener):
    """At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = source.owner_id
        if p_id != event.active_player:
            return
        if (hand_size := len(gs.pile_mgr.hands[p_id])) > 4:
            gs.score_mgr.increment_life(p_id, hand_size - 4, source, gs)


class Karma(Listener):
    """At each player's upkeep, this enchantment deals damage to that player = number of Swamps they control."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        swamp_cnt = len(gs.card_filter.on_player_board(event.active_player).swamps().result())
        if swamp_cnt:
            gs.apply_damage(source, swamp_cnt, event.active_player)


class LandTax(Listener):
    """At your upkeep, if an opponent controls more lands than you, you may:
    search your library for up to 3 basic land cards, reveal them, put them into your hand, then shuffle"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        your_land_cnt = len(gs.card_filter.on_player_board(s.owner_id).lands().result())
        opp_land_cnt = len(gs.card_filter.on_player_board(flip(s.owner_id)).lands().result())
        if not opp_land_cnt > your_land_cnt:
            return
        your_basic_lands = [c for c in gs.pile_mgr.libraries[s.owner_id] if c.props.is_basic_land]
        gs.add_presentation_request(s.owner_id, 'view_library', {'cards': your_basic_lands})
        basic_slug_lands = defaultdict(list)
        for c in your_basic_lands:
            if len(basic_slug_lands.get(c.props.slug)) < 3:
                basic_slug_lands[c.props.slug].append(c)
        basic_lands = [c for slug, cards in basic_slug_lands.items() for c in cards]
        combo_set = {combo for r in range(1, 4) for combo in combinations(basic_lands, r)}
        options = [CO(f"Tutor {', '.join([c for c in list(combo)])}",
                      lambda: self.tutor_cards(gs, s.owner_id, list(combo), Zone.HAND)) for combo in combo_set]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def tutor_cards(gs: GameState, p_id: int, cards: list[GameCard], destination: Zone):
        for c in cards:
            gs.pile_mgr.move_card(c, destination)
        random.shuffle(gs.pile_mgr.libraries[p_id])

class LeviathanUpkeep(Listener):
    """At your upkeep, you may sacrifice two Islands to untap this creature"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != s.owner_id:
            return
        your_islands = gs.card_filter.on_player_board(s.owner_id).islands().result()
        if len(your_islands) < 2:
            return
        options = [CO(f"Sac 2 islands to untap {s}", lambda: self.sac_two_islands_to_untap(gs, s, your_islands))]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def sac_two_islands_to_untap(gs: GameState, s: GameCard, your_islands: list[GameCard]):
        for island in your_islands[:2]:
            gs.pile_mgr.destroy(island)
        s.untap()

class LivingArtifactUpkeep(Listener):
    """... At your upkeep, you may remove a vitality counter from this Aura to gain 1 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        options = [CO(f'Remove a Vitality counter from {source} to gain 1 life',
                      lambda: self.remove_counter_gain_life(gs, source))]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def remove_counter_gain_life(gs: GameState, s: GameCard):
        s.counters.remove_counter(VITALITY)
        gs.score_mgr.increment_life(s.owner_id, 1, s, gs)

class LordOfThePitUpkeep(Listener):
    """At your upkeep, sacrifice a different creature. If you can't, this creature deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        your_other_creatures = [c for c in gs.card_filter.on_player_board(source.owner_id).creatures().result()
                                if c is not source]
        if not your_other_creatures:
            gs.apply_damage(source, 7, source.owner_id)
            return
        options = [CO(f'Sac {c} to {source}', lambda: gs.pile_mgr.sacrifice(c)) for c in your_other_creatures]
        gs.queue_choice(ChoiceAction(options))

class ManaVortexUpkeep(Listener):
    """At each player's upkeep, they sac a land.
    If no lands on entire battlefield, sac this enchantment (handled by ManaVortexSac StateBasedEvent Listener"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        your_lands = gs.card_filter.on_player_board(gs.player_turn_idx).lands().result()
        if len(your_lands) == 1:
            gs.pile_mgr.sacrifice(your_lands[0])
            return
        options = [CO(f'Sac {land}', lambda: gs.pile_mgr.sacrifice(land)) for land in your_lands]
        gs.queue_choice(ChoiceAction(options))

class PowerLeak(Listener):
    """At host owner's upkeep, host owner may pay 0, 1, or 2 mana. PL deals 2 - the mana paid damage to host owner"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        host_owner = source.host.owner_id
        if event.active_player != host_owner:
            return
        available_mana_cnt = sum(gs.mana_pools[host_owner].available_mana.values())
        if available_mana_cnt == 0:
            pay_mana_options = (0, )
        elif available_mana_cnt == 1:
            pay_mana_options = (0, 1)
        else:
            pay_mana_options = (0, 1, 2)
        options = [CO(f'Pay {mana_amt} mana & take {2 - mana_amt} from {source}',
                      lambda: self.pay_mana_take_damage(gs, host_owner, source, mana_amt, 2 - mana_amt))
                   for mana_amt in pay_mana_options]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def pay_mana_take_damage(gs: GameState, p_id: int, s: GameCard, mana_amt: int = 0, damage_amt: int = 0):
        if mana_amt:
            gs.mana_pools[p_id].pay(str(mana_amt))
        if damage_amt:
            gs.apply_damage(s, damage_amt, p_id)

class PowerSurge(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is the number of untapped lands they controlled at the beginning of this turn"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        untapped_lands = gs.card_filter.in_play().untapped().lands().result()
        if untapped_lands:
            gs.apply_damage(source, len(untapped_lands), gs.player_turn_idx)

class PrimordialOoze(Listener):
    """At your upkeep, put a +1/+1 counter on PO.
    Then you may pay {X}, X = +1/+1 counters on it. If you don't, tap PO & it deals X damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        source.counters.add_counter(PLUS_ONE)
        ctr_cnt = source.counters.get_count(PLUS_ONE)
        p_id = source.owner_id
        if not gs.mana_pools[p_id].can_pay(str(ctr_cnt)):
            source.tap()
            gs.apply_damage(source, ctr_cnt, p_id)
            return
        options = [CO(f"Pay {{{str(ctr_cnt)}}}", lambda: gs.mana_pools[source.owner_id].pay(str(ctr_cnt))),
                   CO(f'Tap {source} & take {ctr_cnt} damage',
                      lambda: self.tap_card_take_damage(gs, source, ctr_cnt))]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def tap_card_take_damage(gs: GameState, card: GameCard, damage_amt: int):
        card.tap()
        gs.apply_damage(card, damage_amt, card.owner_id)

class PsychicAllergyDamage(Listener):
    """At opp's upkeep, deal X damage to that opponent. X is their number of nontoken perms of the chosen color"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player == source.owner_id:
            return
        declared_color = source.extras.get('color_declaration')
        opp = flip(source.owner_id)
        cnt = gs.card_filter.on_player_board(opp).by_color(declared_color).non_token().permanents().result()
        if cnt:
            gs.apply_damage(source, cnt, opp)


class PsychicAllergySac(Listener):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        your_islands = gs.card_filter.on_player_board(source.owner_id).islands().result()
        if len(your_islands) < 2:
            gs.pile_mgr.destroy(source)
            return
        options = [CO(f'Sac 2 islands', lambda: self.sac_two_islands(gs, your_islands)),
                   CO(f'Sac {source}', lambda: gs.pile_mgr.sacrifice(source))]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def sac_two_islands(gs: GameState, your_islands: list[GameCard]):
        for island in your_islands[:2]:
            gs.pile_mgr.destroy(island)

class RasputinDreamweaverUpkeep(Listener):
    """... At your upkeep, if RD STARTED THE TURN untapped w < 7 dream counters on it, put a dream counter on it."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if source.extras.get('started_this_turn_untapped') is None:
            return
        if source.extras['started_this_turn_untapped'] and source.counters.get_count(DREAM) < 7:
            source.counters.add_counter(DREAM)


class RogahhOfKherKeepUpkeep(Listener):
    """... At your upkeep, pay {RRR}, else tap Rohgahh & all Kobolds of Kher Keep. Opponent gains control of them."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        owner = source.owner_id
        target_cards = [source] + gs.card_filter.on_player_board(owner).by_slug('kobolds-of-kher-keep').result()
        # action = RogahhOfKherKeepTapAndStealAction(source.owner_id, gs, source, target_cards)
        if not gs.mana_pools[source.owner_id].can_pay('RRR'):
            self.special_action(gs, source, target_cards)
            # action.play()
            return
        options = [CO("Pay {{{'RRR}}}", lambda: gs.mana_pools[source.owner_id].pay('RRR')),
                   CO('Tap & transfer control of Rogahh Of Kher Keep & all Kobolds Of Kher Keep',
                      lambda: self.special_action(gs, source, target_cards))]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def special_action(gs: GameState, s: GameCard, targets: list[GameCard]):
        from models.effects.listeners_mod_queries import OwnershipModQuery
        old_controller = int(s.owner_id)
        new_controller = int(s.owner_id)
        for t in targets:
            t.tap()
            gs.event_mgr.register(OwnershipModQuery(t, lambda gs, s: new_controller), s)
            t.turn_entered_for_owner = gs.turn_mgr.turn_number
            if t.zone == Zone.BATTLEFIELD:
                gs.pile_mgr.boards[old_controller].remove(t)
                gs.pile_mgr.boards[new_controller].append(t)
        gs.event_mgr.emit(StateBasedEvent())

class SafeHavenUpkeep(Listener):
    """At your upkeep, you may sacrifice SH to return all cards it exiled to the battlefield under owner's control"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        options = [CO(f'Sac {source} to return all cards it exiled to the battlefield',
                      lambda: self.return_all_cards_exiled_by(gs, source))]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def return_all_cards_exiled_by(gs: GameState, exiler: GameCard):
        if exiler.extras.get('cards_exiled') is None:
            return
        for card in exiler.extras.get('cards_exiled'):
            gs.pile_mgr.reanimate(card)
        del exiler.extras['cards_exiled']
        gs.pile_mgr.sacrifice(exiler)

class SeasonOfTheWitchUpkeep(Listener):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        options = [CO('Pay 2 life', lambda: gs.score_mgr.decrement_life(source.owner_id, 2, source, gs)),
                   CO(f'Sac {source}', lambda: gs.pile_mgr.sacrifice(source))]
        gs.queue_choice(ChoiceAction(options))

class SerendibDjinn(Listener):
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            gs.pile_mgr.sacrifice(source)
            return
        options = [CO(f"Sac {c}{' & take 3 damage' if c.is_island else ''}",
                      lambda: self.sac_w_damage(gs, source, c, 3 if c.is_island else 0)) for c in your_lands]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def sac_w_damage(gs: GameState, s: GameCard, card: GameCard, damage_amt: int):
        gs.pile_mgr.sacrifice(card)
        if damage_amt:
            gs.apply_damage(s, damage_amt, s.owner_id)

class ShapeshifterUpkeep(Listener):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        options = [CO(f"Set {source}'s power to {n} & toughness to {7 - n}",
                      lambda: self.variable_pt_mod(source, n)) for n in range(8)]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def variable_pt_mod(s: GameCard, n: int):
        p_adj = n - s.power
        t_adj = 7 - n - s.toughness
        s.modifiers.append(PTMod(s=s, p_adj=p_adj, t_adj=t_adj))

class SpiritualSanctuary(Listener):
    """At each player's upkeep, if that player controls a Plains, they gain 1 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if 'plains' in gs.card_filter.on_player_board(event.active_player).plains().result():
            gs.score_mgr.increment_life(event.active_player, 1, source, gs)

class StormWorld(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is 4 minus the number of cards in their hand"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        card_cnt = len(gs.pile_mgr.hands[gs.player_turn_idx])
        if card_cnt > 4:
            gs.apply_damage(source, card_cnt - 4, gs.player_turn_idx)

class TetravusUpkeepCreate(Listener):
    """... At your upkeep, you may remove any number of +1/+1 counters from T to create that many 1/1 colorless
    Tetravite artifact creature tokens, who each have flying and 'This token can't be enchanted.'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != s.owner_id:
            return
        ctr_cnt = s.counters.get_count(PLUS_ONE)
        if not ctr_cnt:
            return
        options = [CO(f'Remove {i} counter(s) from {s} to create {i} Tetravite artifact creature(s)',
                      lambda i=i: self.create_tokens(gs, s, i)) for i in range(1, ctr_cnt + 1)]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def create_tokens(gs: GameState, s: GameCard, cnt: int):
        from models.effects.resolvers_generic import CreateTokenCreature
        s.counters.remove_counter(PLUS_ONE, cnt)
        for _ in range(cnt):
            CreateTokenCreature('tetravite').resolve(gs, s)

class TetravusUpkeepExile(Listener):
    """... At your upkeep, you may exile any number of tokens created with T to put that many +1/+1 counters on T."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != s.owner_id:
            return
        tetravites = gs.card_filter.on_player_board(s.owner_id).by_slug('tetravite').result()
        if not tetravites:
            return
        combos = [combo for r in range(1, len(tetravites) + 1) for combo in combinations(tetravites, r=r)]
        options = [CO(f'Exile {len(combo)} Tetravite(s) to add that many +1/+1 counters to {s}',
                      lambda: self.exile_tokens(gs, s, combo)) for combo in combos]
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def exile_tokens(gs: GameState, s: GameCard, to_be_exiled: list[GameCard]):
        for token in to_be_exiled:
            gs.pile_mgr.exile(token)
            s.counters.add_counter(PLUS_ONE)

class TheAbyss(Listener):
    """At each upkeep, destroy target nonartifact creature that player controls of their choice. No regeneration."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = event.active_player
        your_non_art_creatures = gs.card_filter.on_player_board(p_id).non_artifact_creatures().result()
        if not your_non_art_creatures:
            return
        if len(your_non_art_creatures) == 1:
            target = your_non_art_creatures[0]
            options = [CO(f'Destroy {target}', lambda: gs.pile_mgr.destroy(target, allow_regeneration=False))]
        else:
            options = [CO(f'Destroy {c}', lambda: gs.pile_mgr.destroy(c, False)) for c in your_non_art_creatures]
        gs.queue_choice(ChoiceAction(options))

class TheFallen(Listener):
    """At your upkeep, this creature deals 1 damage to your opponent if it has previously damaged him/her this game"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != source.owner_id:
            return

        from .listeners_damage import DamageResolvedEvent
        for e in gs.event_mgr.events:
            if isinstance(e, DamageResolvedEvent) and e.source is source and e.target == flip(source.owner_id):
                gs.apply_damage(source, 1, flip(source.owner_id))


class TheRack(Listener):
    """At opponent's upkeep, this artifact deals X damage to that player, X = 3 - len(hand) [X can't be negative]"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.pile_mgr.hands[opp_id])
        if opp_hand_len < 3:
            gs.apply_damage(s, 3 - opp_hand_len, opp_id)

class TheTabernacleAtPendrellVale(Listener):
    """All creatures have 'At your upkeep, destroy this creature unless you pay {1}.'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_creature in gs.card_filter.on_player_board(event.active_player).creatures().result():
            if not gs.mana_pools[event.active_player].can_pay('1'):
                gs.pile_mgr.destroy(your_creature)
            options = [CO(f"Pay {{{'1'}}}", lambda: gs.mana_pools[event.active_player].pay('1')),
                       CO(f'Sac {your_creature}', lambda: gs.pile_mgr.sacrifice(your_creature))]
            gs.queue_choice(ChoiceAction(options))

class VesuvanDoppelgangerUpkeep(Listener):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        options = [CO(f'{s} copies {t}', lambda: copy_card(gs, s, t, copy_color=False)) for t in card_options]
        gs.queue_choice(ChoiceAction(options))

class XenicPoltergeistRelease(Listener):
    """{T}: Until your NEXT upkeep, target noncreature artifact becomes an artifact creature with PT each = its MV.
    This effect removes the registered listener at the next upkeep"""
    # TODO: This effect unregisterer should persist even if Xenic Poltergeist leaves battlefield
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.player_turn_idx != source.owner_id:
            return
        gs.event_mgr.unregister_effects(source)

class YawgmothDemon(Listener):
    """At your upkeep, Sac an artifact, or tap this creature & it deals 2 damage to you"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        your_artifacts = gs.card_filter.on_player_board(s.owner_id).artifacts().result()
        if not your_artifacts:
            s.tap()
            gs.apply_damage(s, 2, s.owner_id)
            return
        options = [CO(f'Sac {a}', lambda: gs.pile_mgr.sacrifice(a)) for a in your_artifacts] + \
                  [CO(f'{s} taps and deals 2 damage to you', lambda: self.yd_unpaid_upkeep(gs, s))]
        gs.queue_choice(ChoiceAction(options))

    @staticmethod
    def yd_unpaid_upkeep(gs: GameState, s: GameCard):
        s.tap()
        gs.apply_damage(s, 2, s.owner_id)

class WormsOfTheEarthUpkeep(Listener):
    """... At each upkeep, any player may: do nothing, sac two choice lands, or WOTE deals 5 damage to that player.
    If sac or take the 5 damage, destroy this enchantment."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        options = [CO('Take 5 damage and destroy Worms Of The Earth',
                      lambda: self.take_5_damage(gs, event.active_player, source))]
        your_land_cnt = len(gs.card_filter.on_player_board(event.active_player).lands().result())
        print('xxx', event.active_player, your_land_cnt)
        if your_land_cnt >= 2:
            options.append(CO('Sac two lands and destroy Worms Of The Earth',
                              lambda: self.sac_two_lands(gs, event.active_player, source)))
        gs.queue_choice(ChoiceAction(options, may=True))

    @staticmethod
    def sac_two_lands(gs: GameState, p_id: int, s: GameCard):
        gs.apply_damage(s, 5, p_id)
        gs.pile_mgr.destroy(s)

    @staticmethod
    def take_5_damage(gs: GameState, p_id: int, s: GameCard):
        gs.apply_damage(s, 5, p_id)
        gs.pile_mgr.destroy(s)
