import argparse
import logging
import os
import re

import dateparser
import requests

from .menu import extract_menu

DEFAULT_STORE = os.environ.get('DINNER_DAILY_STORE', 'Any Store')


def login(username, password):
    '''
    Log in to the Dinner Daily website.

    Returns
    -------
    requests.Session
        Use session methods (e.g., ``get()``, ``post()``) to use
        authenticated access.
    '''
    session = requests.Session()
    url = 'https://thedinnerdaily.com/cms/wp-login.php'

    data = {'log': username, 'pwd': password,
            'wp-submit': 'Log In',
            'redirect_to': 'https://thedinnerdaily.com/cms/wp-admin/',
            'testcookie': 1}
    headers = {'referer': 'https://thedinnerdaily.com/'}
    response = session.get(url)
    response = session.post(url, data=data, headers=headers)
    assert(response.status_code == 200)
    return session


def download(week_, output_dir, session=None, username=None, password=None,
             store=DEFAULT_STORE):
    '''
    .. versionchanged:: X.X.X
        Parse start date from new ``<month> <start> to <end>`` format (e.g.,
        ``Oct 28 to 03``).
    .. versionchanged:: X.X.X
        Add ``username`` and ``password`` kwargs. Use these to authenticate
        session for download.
    '''
    if week_ not in ('current', 'previous'):
        raise ValueError('`week` must be either `current` or `previous`.')

    base_url = 'https://db.thedinnerdaily.com/menus/'

    if session is None:
        if any((username is None, password is None)):
            raise ValueError('Either `session` or `username` _and_ `password` '
                             'must be specified.')
        else:
            session = login(username, password)

    # Download weekly menu using browser cookies.
    menu_response = session.get(base_url + 'print/%s/%s' % (store, week_))
    # Scrape date from menu HTML to use in file name.
    menu = extract_menu(menu_response.text)
    menu['date'] = re.sub(r' to .*', '', menu['date'])
    menu_date = dateparser.parse(menu['date'])
    # Download weekly shopping list using browser cookies.
    list_response = session.get(base_url + 'print-shopping-list/%s/%s' %
                                (store, week_))

    cwd = os.getcwd()
    try:
        os.chdir(output_dir)
        out_name_fmt = '%s-%%s-%s.html' % (menu_date.strftime('%Y-%m-%d'),
                                           store)

        out_name = out_name_fmt % 'weekly-menu'
        with open(out_name, 'w') as output:
            output.write(menu_response.text)
        logging.info('Wrote weekly menu to: `%s`' % out_name)

        out_name = out_name_fmt % 'shopping-list'
        with open(out_name, 'w') as output:
            output.write(list_response.text)
        logging.info('Wrote weekly menu to: `%s`' % out_name)
    finally:
        os.chdir(cwd)



def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('week', choices=('current', 'previous'))
    parser.add_argument('--username',
                        default=os.environ.get('DINNER_DAILY_USERNAME'),
                        help='Dinner Daily username (default: '
                        '`DINNER_DAILY_USERNAME` environment variable).')
    parser.add_argument('--password',
                        default=os.environ.get('DINNER_DAILY_PASSWORD'),
                        help='Dinner Daily password (default: '
                        '`DINNER_DAILY_PASSWORD` environment variable).')
    parser.add_argument('--store', default=DEFAULT_STORE, help='Store '
                        '(default: %(default)s)')
    parser.add_argument('output_dir', help='Output directory.')

    return parser.parse_args()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    download(args.week, args.output_dir, username=args.username,
             password=args.password, store=args.store)