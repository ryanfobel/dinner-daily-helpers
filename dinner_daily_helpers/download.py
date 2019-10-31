import argparse
import logging
import os
import re

import dateparser

from .memoized import cookie_request, DEFAULT_STORE
from .menu import extract_menu


def download(week_, output_dir, store=DEFAULT_STORE):
    '''
    .. versionchanged:: X.X.X
        Parse start date from new ``<month> <start> to <end>`` format (e.g.,
        ``Oct 28 to 03``).
    '''
    if week_ not in ('current', 'previous'):
        raise ValueError('`week` must be either `current` or `previous`.')

    base_url = 'https://db.thedinnerdaily.com/menus/'

    # Download weekly menu using browser cookies.
    menu_response = cookie_request(base_url + 'print/%s/%s' % (store, week_))
    # Scrape date from menu HTML to use in file name.
    menu = extract_menu(menu_response.text)
    menu['date'] = re.sub(r' to .*', '', menu['date'])
    menu_date = dateparser.parse(menu['date'])
    # Download weekly shopping list using browser cookies.
    list_response = cookie_request(base_url + 'print-shopping-list/%s/%s' %
                                   (store, week_))

    cwd = os.getcwd()
    try:
        os.chdir(output_dir)
        out_name_fmt = '%s-%%s-%s.html' % (menu_date.strftime('%Y-%m-%d'),
                                           store)

        out_name = out_name_fmt % 'weekly-menu'
        with open(out_name, 'w') as output:
            output.write(menu_response.text.encode('utf8'))
        logging.info('Wrote weekly menu to: `%s`' % out_name)

        out_name = out_name_fmt % 'shopping-list'
        with open(out_name, 'w') as output:
            output.write(list_response.text.encode('utf8'))
        logging.info('Wrote weekly menu to: `%s`' % out_name)
    finally:
        os.chdir(cwd)



def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('week', choices=('current', 'previous'))
    parser.add_argument('--store', default=DEFAULT_STORE, help='Store '
                        '(default: %(default)s)')
    parser.add_argument('output_dir', help='Output directory.')

    return parser.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    download(args.week, args.output_dir, store=args.store)
