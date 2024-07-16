"""Expose crawler for InBerlinWohnen"""
import re
import datetime

from bs4 import Tag

from flathunter.webdriver_crawler import WebdriverCrawler
from flathunter.logging import logger

class InBerlinWohnen(WebdriverCrawler):
    """Implementation of Crawler interface for InBerlinWohnen"""

    URL_PATTERN = re.compile(r'inberlinwohnen')

    def get_expose_details(self, expose):
        soup = self.get_page(expose['url'], self.get_driver())
        if 'from' not in expose:
            expose['from'] = datetime.datetime.now().strftime('%02d.%02m.%Y')
        return expose

    # pylint: disable=too-many-locals
    def extract_data(self, soup):
        """Extracts all exposes from a provided Soup object"""
        entries = []
        soup = soup.find(id="_tb_relevant_results")

        expose_ids = soup.find_all(class_="tb-merkflat ipg")

        for idx, exposes in enumerate(expose_ids):
            try:
                href = "---"
                org_but_string = str(expose_ids[idx].find(class_="org-but", href=True))
                org_but_split = org_but_string.split()

                for index, item in enumerate(org_but_split):
                    if item.startswith('href'):
                        href = org_but_split[index][6:-1]

            except AttributeError as error:
                logger.warning("Unable to process inBerlinWohnen expose URL: %s", str(error))
                continue

            try:
                title = "---"
                merkdetails_string = expose_ids[idx].find(class_="tb-merkdetails").text.strip()
                merkdetails_split = merkdetails_string.split('\n')

                title = merkdetails_split[0]

            except AttributeError as error:
                logger.warning("Unable to process inBerlinWohnen expose title: %s", str(error))
                continue


            try:
                tb_left_string = expose_ids[idx].find(class_="_tb_left").text.strip()
                tb_left_split = tb_left_string.split()

                price = "---"
                address = "---"

                for index, item in enumerate(tb_left_split):
                    if item.startswith('€'):
                        price = tb_left_split[index - 1]
                    elif item.startswith('|'):
                        address = tb_left_split[index + 1]
                        if(index + 2 < len(tb_left_split)):
                            address += ' ' + tb_left_split[index + 2]
                        if(index + 3 < len(tb_left_split)):
                            address += ' ' + tb_left_split[index + 3]
                        if(index + 4 < len(tb_left_split)):
                            address += ' ' + tb_left_split[index + 4]
                        if(index + 5 < len(tb_left_split)):
                            address += ' ' + tb_left_split[index + 5]

                rooms = tb_left_split[0]
                size = tb_left_split[2]

            except AttributeError as error:
                logger.warning("Unable to process inBerlinWohnen expose: %s", str(error))
                continue


            details = {
                'id': int(expose_ids[idx].get("id")[6:]),
                'image': None,
                'url': ("https://www.inberlinwohnen.de/wohnungsfinder" + href),
                'title': (title + "\n"),
                'price': (price  + " €"),
                'size': (size + " m²"),
                'rooms': rooms,
                'address': address,
                'crawler': self.get_name()
            }
            entries.append(details)

        logger.debug('Number of entries found: %d', len(entries))

        return entries