from dataclasses import dataclass
from pathlib import Path

from common.file_utils import read_json_file, write_to_json_file_one_line_per_key

FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "users.json"

@dataclass
class UserData:
    user_id: str
    handle: str
    card_sort: str

def get_users() -> list[UserData]:
    data = read_json_file(FILE_PATH)
    return [UserData(k, v['handle'], v['card_sort']) for k, v in data.items()]

def get_user(user_id: str) -> UserData:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k == user_id:
            return UserData(k, v['handle'], v['card_sort'])

def update_user(user_id: str, handle: str, card_sort: str) -> None:
    data = read_json_file(FILE_PATH)
    for k, v in data.items():
        if k != user_id:
            continue
        v['handle'] = handle
        v['card_sort'] = card_sort
    write_to_json_file_one_line_per_key(FILE_PATH, data)

