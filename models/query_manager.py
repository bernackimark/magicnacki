from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base_rules_queries import CanAttackRule, CanBlockRule, CanCastRule, CanDamageRule, CanTargetRule

if TYPE_CHECKING:
    from game_state import GameState
    from models.effects.base import Effect
    from models.game_card.game_card import GameCard


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

    def _query_effects(self, query: str, card: GameCard, **kwargs) -> bool:
        """Ask all query-style effects (base, card, and until_eots) if they have an opinion;
        can be True (which is either hard permission or the lack of a hard-veto) or False (a hard veto);
        hard permission takes precedence over hard veto;
        hard permission ex: undertow & islandwalkers can be blocked;
        hard veto ex: meekstone preventing some untaps"""
        effects = (self._base_queries +
                   [a.effect for c in self._gs.card_filter.in_play().result()
                    for a in c.static_abilities + c.triggered_abilities] +
                   [eff for eff, _ in self._gs.until_eot_effects_and_cards])

        explicit_forbids = False
        for eff in effects:
            if not hasattr(eff, 'on_query') or not hasattr(eff, 'query') or eff.query != query:
                continue

            result = eff.on_query(self._gs, card=card, **kwargs)

            if result is True:
                return True
            if result is False:
                explicit_forbids = True
        return False if explicit_forbids else True
