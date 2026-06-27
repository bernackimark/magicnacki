from __future__ import annotations

def create_target_text(targets: int | "GameCard" | tuple | list | None):
    from models.game_card.game_card import GameCard
    """0 -> ', targeting Player #0' ... [1, c1] -> ', targeting Player #1, Air Elemental'
    (0, 1) -> ', targeting Player #0, Player #1' ... [c1, c2] -> , 'targeting Air Elemental, Savannah Lions'"""
    from models.game_card.game_card import GameCard
    if not targets:
        return ''
    if isinstance(targets, int):
        return f', targeting Player #{targets}'
    if isinstance(targets, GameCard):
        return ', targeting ' + targets.props.name
    begin_text = ', targeting'
    target_texts = []
    for t in targets:
        target_text = t.props.name if isinstance(t, GameCard) else f'Player #{t}'
        target_texts.append(target_text)
    return f"{begin_text} {', '.join(target_texts)}"
