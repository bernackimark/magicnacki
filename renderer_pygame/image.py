"""A module to save images from website links"""
import json
from pathlib import Path
import requests

from config import SCRYFALL_FILE_PATH, IMAGES_OUTPUT_PATH2


def download_image(url: str, save_to_path_str: str):
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    with open(save_to_path_str, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)


def save_image(link: str, output_dir_str: str, output_file_name: str):
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    card_dir = output_dir / slug
    card_dir.mkdir(parents=True, exist_ok=True)

    download_image(link, card_dir / f"{output_file_name}.jpg")


if __name__ == '__main__':
    if input("Are you sure you want to create all these image files? (Y/n) ") != 'Y':
        exit()
    path = Path(SCRYFALL_FILE_PATH)
    with path.open("r", encoding="utf-8") as f:
        file_w_links = json.load(f)
    for slug, card_data in file_w_links.items():
        desired_image_keys = ['border_crop', 'art_crop']
        for set_code, set_data in card_data['sets'].items():
            for key in desired_image_keys:
                save_image(set_data['image_uris'][key], IMAGES_OUTPUT_PATH2, f'{set_code}-{key}')
                print(f'Saved {key} for {slug}')

