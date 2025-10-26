from dataclasses import dataclass, field
import json
import re

from file_utils import write_json_to_file
import requests

from file_utils import update_json_file_with_dict
from scraping import (scrape_pages_until_text_not_found, find_all_matched, find_all_matched_until,
                      find_first_match, clean_raw_html)


@dataclass
class CardScraper:
    set_code: str
    start_page_num: int = 1
    end_page_num: int = 100
    LANDS = ['forest', 'island', 'mountain', 'plains', 'swamp']
    base_url: str = field(init=False)

    def __post_init__(self):
        self.base_url = f'https://gatherer.wizards.com/sets/{self.set_code}?display=hybrid&sortBy=CardName&sortOrder=Ascending&page='

    def scrape_card_slugs(self) -> list[str]:
        page_scrapes: list[str] = scrape_pages_until_text_not_found(self.base_url, f'href="/{self.set_code}/en-us/0/',
                                                                    self.start_page_num, self.end_page_num)
        card_slugs = []
        for scrape in page_scrapes:
            slugs = find_all_matched(scrape, [f'href="/{self.set_code}/en-us/0/', f'href="/{self.set_code}/en-us/0a/'], '"')
            # basic lands are /0a/; all others are /0/
            card_slugs.extend(slugs[:-1])  # website captures the 1st name a 2nd time at the end
        print(f'Successfully scraped slugs for set code: {self.set_code}')
        return card_slugs

    def _get_card_url(self, slug: str) -> str:
        land_sub_str = '0a' if slug in self.LANDS else '0'
        return f'https://gatherer.wizards.com/{self.set_code}/en-us/{land_sub_str}/{slug}'

    def scrape_card_data(self, specific_slug: str = None) -> dict:
        card_slugs = self.scrape_card_slugs() if not specific_slug else [specific_slug]
        cards_data = {}
        for slug in card_slugs:
            # try:
            url = self._get_card_url(slug)
            print('Scraping', url)
            html_str = requests.get(url).text
            print(f'Found {len(html_str)} characters')
            # Step 1: Capture the JS string starting with 34:
            pattern = re.compile(r'self\.__next_f\.push\(\[1,"34:(.*?)"\]\)', re.DOTALL)
            match = pattern.search(html_str)

            if not match:
                raise ValueError("Could not find '34:' block.")

            # Step 2: Extract the captured part
            raw_js = match.group(1)

            # Step 3: Decode escaped characters (\" -> ", \\ -> \, etc.)
            decoded = raw_js.encode("utf-8").decode("unicode_escape")

            # Step 4: Parse the JSON array (the decoded string starts with [ ... ])
            data = json.loads(decoded)

            # Step 5: Recursively find the 'card' object
            def find_card(obj):
                if isinstance(obj, dict):
                    if "card" in obj:
                        return obj["card"]
                    for v in obj.values():
                        found = find_card(v)
                        if found:
                            return found
                elif isinstance(obj, list):
                    for v in obj:
                        found = find_card(v)
                        if found:
                            return found
                return None

            card_data = find_card(data)

            # Step 6: Output
            cards_data[slug] = card_data
        return {self.set_code: cards_data}

    def get_html_for_specific_card(self, set_code: str, slug: str):
        """debugging convenience method"""
        land_sub_str = '0a' if slug in self.LANDS else '0'
        url = f'https://gatherer.wizards.com/{set_code}/en-us/{land_sub_str}/{slug}'
        return requests.get(url).text


if __name__ == '__main__':
    ...  # TODO: presently broken.  works for one card, but getting a JSON Decode error
    ...  # the idea behind this approach is to parse the JS Schema data into JSON right away, instead of scraping HTML
    # card_scraper = CardScraper('5E')
    # data = card_scraper.scrape_card_data()
    # update_json_file_with_dict('card_data20251015.json', data)
    #
    # cs2 = CardScraper('4E')
    # data = cs2.scrape_card_data()
    # update_json_file_with_dict('card_data20251015.json', data)
