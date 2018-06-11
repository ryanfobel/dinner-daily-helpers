from __future__ import unicode_literals, print_function
import datetime as dt
import io

import bs4
import dinner_daily_helpers as ddh


def dump_list(df_ingredients):
    soup = bs4.BeautifulSoup(df_ingredients.to_html(), 'html5lib')

    table = soup.find('table')
    table.attrs['class'] = 'table table-striped'
    del table.attrs['border']


    with io.StringIO() as tf:
        tf.write(r'''
    <html>
    <head>
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">

    <!-- Optional theme -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">
    </head>
    <body>
    '''.strip())
        tf.write(soup.prettify())
        tf.write(r'''
    </body>
    </html>
    ''')
        return tf.getvalue()


if __name__ == '__main__':
    this_week = ddh.week(dt.datetime.now())
    shopping_list_html = ddh.fetch_shopping_list_html(this_week)
    df_ingredients = ddh.get_section_ingredients(shopping_list_html)
    print(dump_list(df_ingredients))
