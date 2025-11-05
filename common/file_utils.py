import json
from pathlib import Path


def update_json_file_with_dict(file_path: str | Path, new_dict: dict) -> None:
    """
    Update a JSON file that contains a single dictionary.
    - If the file doesn't exist, create it with `new_dict`.
    - If the file exists, merge `new_dict` into the existing dictionary.
    """
    if input(f"Are you sure you want to update '{file_path}'? (Y/n) ") != 'Y':
        return

    file_path = Path(file_path)
    data = {}

    # Step 1: Load existing dictionary if file exists
    if file_path.exists():
        text = file_path.read_text(encoding="utf-8")
        if text.strip():  # non-empty file
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError(f"{file_path} does not contain a dictionary.")

    # Step 2: Merge new_dict into existing dictionary
    data.update(new_dict)

    # Step 3: Write the updated dictionary back to file
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json_file(file_path: str | Path) -> dict:
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def write_json_to_file(file_path: str | Path, new_dict: dict):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(new_dict, f, indent=2, ensure_ascii=False)
