#  a module to create images from website links
from io import BytesIO
from pathlib import Path

from file_utils import read_json_file
from PIL import Image
import requests

# TODO: get these into an .env file
URL_FILE_PATH = Path('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/gatherer/card_data.json')
OUTPUT_PATH = Path('/Users/Bernacki_Laptop/PycharmProjects/magicnacki/renderer_pygame/assets/images/')

OUTPUT_EXTENSION = '.jpg'

def get_bytes_from_url(url: str):
    return requests.get(url).content


def create_image_object(bytes_obj: bytes, is_output_jpg: bool = True) -> Image:
    image = Image.open(BytesIO(bytes_obj))
    if is_output_jpg:
        image = image.convert("RGB")  # JPG doesn't support transparency
    return image


def save_image_file(image_object: Image, file_path_dir: Path, file_name: str, file_ext: str = '.jpg') -> None:
    """Accepts a Pillow Image, creates a .jpg file, and saves it to a Path directory / file_name.file_ext """
    # TODO: "JPEG" is hard-coded; not sure what other file types Pillow can save as ...
    output_path = file_path_dir / f'{file_name}{file_ext}'
    output_path.parent.mkdir(exist_ok=True)
    image_object.save(output_path, "JPEG")


if __name__ == '__main__':
    if input("Are you sure you want to create all these image files? (Y/n) ") != 'Y':
        exit()
    file_w_links: dict[str: dict[str: str]] = read_json_file(URL_FILE_PATH)
    for set_code, set_data in file_w_links.items():
        for slug, card_data in set_data.items():
            url = card_data['img_url']
            bytes_ = get_bytes_from_url(url)
            image_obj = create_image_object(bytes_)
            image_file_name = set_code
            save_image_file(image_obj, OUTPUT_PATH / slug, image_file_name)
            print(f'Saved {image_file_name} {slug}')

