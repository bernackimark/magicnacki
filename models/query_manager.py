from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base_rules_queries import CanAttackRule, CanBlockRule, CanCastRule, CanDamageRule, CanTargetRule

if TYPE_CHECKING:
    from game_state import GameState
    from models.effects.base import Effect
    from models.game_card.game_card import GameCard
    from models.modifiers import ModType


class QueryManager:
    def __init__(self, gs: GameState):
        self._base_queries: list[Effect] = [CanAttackRule(), CanBlockRule(), CanCastRule(),
                                            CanDamageRule(), CanTargetRule()]
        self._gs = gs

    def can_attack(self, card: GameCard) -> bool:
        return self._query_effects('can_attack', card)

    def can_be_destroyed(self, card: GameCard) -> bool:
        result = self._query_effects('can_be_destroyed', card)
        return False if result is False else True

    def can_block(self, blocker: GameCard, attacker: GameCard) -> bool:
        return self._query_effects('can_block', blocker, attacker=attacker)

    def can_cast(self, card: GameCard, p_id: int) -> bool:
        return self._query_effects('can_cast', card, p_id=p_id)

    def can_damage(self, target: GameCard, source: GameCard) -> bool:
        return self._query_effects('can_damage', target, source=source)

    def can_target(self, target: GameCard | int, source: GameCard, target_host: GameCard | None = None) -> bool:
        if isinstance(target, int):
            return True
        result = self._query_effects('can_target', target, source=source, target_host=target_host)
        return False if result is False else True

    def can_untap(self, card: GameCard) -> bool:
        return self._query_effects('can_untap', card)

    def _get_effects(self) -> list[Effect]:
        return (self._base_queries +
                   [a.effect for c in self._gs.card_filter.in_play().result()
                    for a in c.static_abilities + c.triggered_abilities])

    def _query_effects(self, query: str, card: GameCard, **kwargs) -> bool:
        """Ask all query-style effects (base, card, and until_eots) if they have an opinion;
        can be True (which is either hard permission or the lack of a hard-veto) or False (a hard veto);
        hard permission takes precedence over hard veto;
        hard permission ex: undertow & islandwalkers can be blocked;
        hard veto ex: meekstone preventing some untaps"""
        explicit_forbids = False
        for eff in self._get_effects():
            if not hasattr(eff, 'on_query') or not hasattr(eff, 'query') or eff.query != query:
                continue

            result = eff.on_query(self._gs, card=card, **kwargs)

            if result is True:
                return True
            if result is False:
                explicit_forbids = True
        return False if explicit_forbids else True

    # def get_global_modifiers(self, global_type: str, card: GameCard) -> list[ModType]:
    #     """Some mods are stored on the card itself locally (attached auras);
    #     some mods need to be retrieved from other cards (ex: Crusade returns a PTMod for white creatures)"""
    #     effects_and_cards: list[tuple[Effect, GameCard]] = []
    #     # static effects on other permanents (ex: crusade lives in static abilities)
    #     for c in self._gs.card_filter.in_play().result():
    #         for a in c.static_abilities:
    #             effects_and_cards.append((a.effect, c))
    #         for a in c.triggered_abilities:
    #             effects_and_cards.append((a.effect, c))
    #
    #     modifiers = []
    #     for effect, source in effects_and_cards:
    #         if not hasattr(effect, 'get_mods') or not hasattr(effect, 'modifies'):
    #             continue
    #         if isinstance(effect.query, str) and effect.query != global_type:
    #             continue
    #         if isinstance(effect.query, tuple) and global_type not in effect.query:
    #             continue
    #         mod: ModType | list[ModType] | None = effect.get_mods(self._gs, global_type,
    #                                                               card=card, source=source)
    #         if mod:
    #             modifiers.append(mod) if isinstance(mod, ModType) else modifiers.extend(mod)
    #     return modifiers
