from dataclasses import dataclass, asdict
from pathlib import Path

from common.file_utils import read_json_file, write_to_json_file_one_line_per_key, update_json_file_with_dict

FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "users.json"

@dataclass
class UserData:
    user_id: str
    handle: str
    is_bot: bool
    card_sort: str

def get_users() -> list[UserData]:
    data = read_json_file(FILE_PATH)
    return [UserData(k, v['handle'], v['is_bot'], v['card_sort']) for k, v in data.items()]

def get_user(user_id: str) -> UserData:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k == user_id:
            return UserData(k, v['handle'], v['is_bot'], v['card_sort'])

def update_user(user_id: str, handle: str, card_sort: str) -> None:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k != user_id:
            continue
        v['handle'] = handle
        v['card_sort'] = card_sort
    write_to_json_file_one_line_per_key(FILE_PATH, data)

def create_user(handle: str, is_bot: bool = False, card_sort: str = 'A'):
    users = get_users()
    if handle in {u.handle for u in users}:
        raise ValueError(f'That handle is already taken')
    user_id = str(max([int(u.user_id) for u in users]) + 1) if users else "0"
    record = {user_id: {'handle': handle, 'is_bot': is_bot, 'card_sort': card_sort}}
    update_json_file_with_dict(FILE_PATH, record)


"""
{
  "0": {
    "handle": "Mark",
    "is_bot": false,
    "card_sort": "A"
  },
  "1": {
    "handle": "Bull",
    "is_bot": false,
    "card_sort": "B"
  }
}
"""
