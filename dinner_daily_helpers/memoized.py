import calendar
import datetime as dt
import os
import os.path

from joblib import Memory
import browsercookie
import requests


__all__ = ['fetch_shopping_list_html', 'fetch_weekly_menu_html', 'week',
           'this_week', 'last_week', 'DEFAULT_STORE']

DEFAULT_STORE = os.environ.get('DINNER_DAILY_STORE', 'Any Store')

memoize_memory = Memory(cachedir=os.path.expanduser('~/.dinner-daily-helpers'),
                        verbose=0)


def this_week():
    return week(dt.datetime.now())


def last_week():
    return week(dt.datetime.now() - dt.timedelta(days=7))


def week(datetime_):
    weekday = calendar.weekday(datetime_.year, datetime_.month, datetime_.day)
    start_of_week = (datetime_ if weekday == calendar.SATURDAY else datetime_ -
                     dt.timedelta(days=(weekday - calendar.SATURDAY) % 7))
    return (datetime_.year, ((start_of_week.date() -
                              dt.date(datetime_.year, 1, 1)).days // 7) + 1)


def cookie_request(url):
    # Use cookies from browser to provide access.
    cj = browsercookie.load()

    with requests.Session() as session:
        response = session.get(url, cookies=cj)
    return response


@memoize_memory.cache
def fetch_shopping_list_html(week_, store=DEFAULT_STORE):
    # Select URL based on specified week.
    if week_ == this_week():
        relative_week = 'current'
    elif week_ == last_week():
        relative_week = 'previous'
    else:
        raise ValueError('Week must be either: `%s` or `%s`' % (this_week(),
                                                                last_week()))
    url = ('https://db.thedinnerdaily.com/menus/print-shopping-list/%s/%s'
           % (store, relative_week))

    response = cookie_request(url)
    if response.status_code != 200:
        raise IOError('Error fetching shopping list.  Make sure you have '
                      'logged in through your browser on the computer running '
                      'this script.')
    return response.text


@memoize_memory.cache
def fetch_weekly_menu_html(week_, store=DEFAULT_STORE):
    # Select URL based on specified week.
    if week_ == this_week():
        relative_week = 'current'
    elif week_ == last_week():
        relative_week = 'previous'
    else:
        raise ValueError('Week must be either: `%s` or `%s`' % (this_week(),
                                                                last_week()))
    url = ('https://db.thedinnerdaily.com/menus/print/%s/%s' %
           (store, relative_week))
    response = cookie_request(url)
    if response.status_code != 200:
        raise IOError('Error fetching weekly menu.  Make sure you have '
                      'logged in through your browser on the computer running '
                      'this script.')
    return response.text
