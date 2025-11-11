def get_all_creatures(gs: "GameState") -> list["GameCard"]:
    return [c for b in gs.boards for c in b.cards if c.props.is_creature]

def send_all_creatures_to_graveyard(gs: "GameState") -> None:
    for c in get_all_creatures(gs):
        gs.send_to_graveyard(c)


game_card_abilities = [

]

