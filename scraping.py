import html
import re

import requests


def scrape_pages_until_text_not_found(base_url: str, required_text: str,
                                      begin_page_num: int = 0, end_page_num: int = 100) -> list[str]:
    """Ex base_url: http://www.example.com/page/  ex required_text: 'item_price' ...
    for range(begin_page_num, end_page_num), if the page contains 'item_price' ...
    return each html as a string in a list of pages"""
    page_scrapes: list[str] = []
    for i in range(begin_page_num, end_page_num + 1):
        url_w_page_number = f'{base_url}{i}'
        print('Scraping', url_w_page_number)
        page_scrape = requests.get(url_w_page_number).text
        print(f'Found {len(page_scrape)} characters')
        if required_text not in page_scrape:
            print(f'Stopping scrape as required text: "{required_text}" not found on page: {url_w_page_number}')
            break
        page_scrapes.append(page_scrape)
    return page_scrapes


def find_all_matched(html_str: str, preceding_text: list[str] | str, succeeding_text: str) -> list[str]:
    """string of 'abcdefg xZfg', preceding_texts = ['ab', 'x'] & succeeding_text = 'fg', returns ['cde', 'Z'].
    succeeding text should be r-string"""
    # Regex pattern: look for any of the targets and capture everything until next quote
    if isinstance(preceding_text, list):
        pattern = re.compile(r'(?:' + '|'.join(map(re.escape, preceding_text)) + f')(.*?){succeeding_text}')
    else:
        pattern = re.compile(re.escape(preceding_text) + f'(.*?){succeeding_text}')
    return pattern.findall(html_str)

def find_all_matched_until(html_str: str, preceding_text: list[str] | str, succeeding_text: str, until_text: str) -> list[str]:
    """like find_all_matched() except it will stop looking when it encounters until_text"""
    until_text_pos: int = html_str.find(until_text)
    if until_text_pos == -1:
        return find_all_matched(html_str, preceding_text, succeeding_text)
    html_str = html_str[:until_text_pos]
    return find_all_matched(html_str, preceding_text, succeeding_text)


def find_first_match(html_str: str, preceding_text: list[str] | str, succeeding_text: str) -> str | None:
    """ex html_str='abcdefg xZfg', preceding_text='abc', succeeding_text='Zfg', returns 'defg x' """
    if isinstance(preceding_text, list):
        pattern = re.compile(r'(?:' + '|'.join(map(re.escape, preceding_text)) + f')(.*?){succeeding_text}')
    else:
        pattern = re.compile(re.escape(preceding_text) + f'(.*?){succeeding_text}')
    match = re.search(pattern, html_str)
    return match.group(1) if match else None


def clean_raw_html(text: str) -> str:
    """handles HTML entities like &amp;, &#x27; replaces characters like \\\\\n, \\t, \\\\ with a space"""
    tmp1 = html.unescape(text)  # html.unescape handles HTML entities like &amp;, &#x27;
    tmp2 = re.sub(r'\\+n', ' ', tmp1)  # handles escaped characters like \\\\n, \\t, \\\"
    return tmp2
