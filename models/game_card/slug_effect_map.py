from .slug_effect_map_a_to_e import MAP as MAP1
from .slug_effect_map_f_to_o import MAP as MAP2
from .slug_effect_map_p_to_z import MAP as MAP3
from ..effects.base import EffSpec

"""Stitch together smaller slug-effect maps; one consolidated map created IDE performance issues during development
WARNING: In the effects list, CastResolvedEvent must currnetly be listed last, else no others will be registered
"""

INVOCATIONS: dict[str, list[EffSpec]] = {}
INVOCATIONS.update(MAP1)
INVOCATIONS.update(MAP2)
INVOCATIONS.update(MAP3)
