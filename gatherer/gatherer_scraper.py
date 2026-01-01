from dataclasses import dataclass, field

import requests

from common.file_utils import update_json_file_with_dict
from scraping import (scrape_pages_until_text_not_found, find_all_matched, find_first_match, clean_raw_html)

SLUGS_W_0A_URLS = {'army-of-allah', 'bird-maiden'}

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

    @staticmethod
    def _clean_rules_text(text: str) -> str:
        text = text[:-1]  # removes backslash in the succeeding text
        text = clean_raw_html(text)
        text = text.replace('\\', '').replace('  ', ' ')
        return text

    @staticmethod
    def _clean_js_schema_list(text: str) -> list:
        tmp1 = '[' + text + ']'
        tmp2 = tmp1.encode('utf-8').decode('unicode_escape')
        return eval(tmp2)  # convert string to other Python objects like list or dict

    def scrape_card_data(self, specific_slug: str = None) -> dict:
        card_slugs = self.scrape_card_slugs() if not specific_slug else [specific_slug]
        cards_data = {}
        for slug in card_slugs:
            # try:
            for url_sub_str in ('0', '0a'):
                url = f'https://gatherer.wizards.com/{self.set_code}/en-us/{url_sub_str}/{slug}'
                print('Scraping', url)
                html_str = requests.get(url).text
                print(f'Found {len(html_str)} characters')

                # Card Not Found HTML seems to be under 60_000 chars, successes much greater
                if len(html_str) >= 75000 or slug in self.LANDS:
                    break
                print(f'Likely URL failure for {url}; attempting to use "0a" URL')

            if len(html_str) < 75000:
                raise ValueError(f'Exiting ... Scrape likely failed for {url}\nHere is the HTML dump:\n{html_str}')

            name = find_first_match(html_str, '"cardDetailsCardName">', '</')
            name = clean_raw_html(name)
            casting_cost = find_first_match(html_str, 'instanceManaText\\":\\"', '\\\\"')
            card_type = find_first_match(html_str, 'cardDetailsTypeLine">', '<')
            rarity = find_first_match(html_str, 'cardDetailsRarity">', '<')
            rules_text = find_first_match(html_str, 'instanceText\\":\\"', '\\",')
            if rules_text:
                rules_text = self._clean_rules_text(rules_text)
            oracle_rules_text = find_all_matched(html_str, 'oracleText\\":\\"', '\\",')[-1]
            if oracle_rules_text:
                oracle_rules_text = self._clean_rules_text(oracle_rules_text)
            power = find_first_match(html_str, 'cardDetailsPower">', '<')
            toughness = find_first_match(html_str, 'cardDetailsToughness">', '<')
            card_types_str = find_first_match(html_str, 'instanceTypes\\":[', '],')
            card_types = self._clean_js_schema_list(card_types_str)
            card_sub_types_str = find_first_match(html_str, 'instanceSubtypes\\":[', '],')
            card_sub_types = self._clean_js_schema_list(card_sub_types_str)
            card_super_types_str = find_first_match(html_str, 'instanceSupertypes\\":[', '],')
            card_super_types = self._clean_js_schema_list(card_super_types_str)
            img_url = find_first_match(html_str, 'frontSrc\\":\\"', '\\"')
            if img_url:
                img_url = img_url[:-1]  # removes backslash in the succeeding text
            rulings = find_first_match(html_str, '"rulings\\":[', '],') or []
            if rulings:
                rulings_as_list = self._clean_js_schema_list(rulings)
                for d in rulings_as_list:
                    d['ruling_date'] = d.pop('rulingDate')
                    d['ruling_statement'] = d.pop('rulingStatement')
                rulings = rulings_as_list
            cards_data[slug] = {'name': name, 'casting_cost': casting_cost, 'card_type': card_type,
                                'rarity': rarity,
                                'rules_text': rules_text, 'oracle_rules_text': oracle_rules_text,
                                'power': power, 'toughness': toughness,
                                'img_url': img_url, 'data_url': url, 'rulings': rulings,
                                'card_types': card_types, 'card_sub_types': card_sub_types,
                                'card_super_types': card_super_types}
            # except:
            #     print(f"Something failed when scraping data for slug: {slug} at: {url}. Here's the HTML: {html_str}")
            #     break
        return {self.set_code: cards_data}

    def get_html_for_specific_card(self, set_code: str, slug: str):
        """debugging convenience method"""
        land_sub_str = '0a' if slug in self.LANDS else '0'
        url = f'https://gatherer.wizards.com/{set_code}/en-us/{land_sub_str}/{slug}'
        return requests.get(url).text


if __name__ == '__main__':
    card_scraper = CardScraper('AN')
    data = card_scraper.scrape_card_data()
    update_json_file_with_dict('card_data.json', data)

    card_scraper = CardScraper('AQ')
    data = card_scraper.scrape_card_data()
    update_json_file_with_dict('card_data.json', data)

    card_scraper = CardScraper('LE')
    data = card_scraper.scrape_card_data()
    update_json_file_with_dict('card_data.json', data)

    card_scraper = CardScraper('DK')
    data = card_scraper.scrape_card_data()
    update_json_file_with_dict('card_data.json', data)
