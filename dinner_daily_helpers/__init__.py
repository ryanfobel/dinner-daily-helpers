# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import itertools as it
import re

import bs4
import pandas as pd
import pint


ureg = pint.UnitRegistry(system='cgs')

# Add non-default units used by Dinner Daily.
ureg.define('bulb = []')
ureg.define('bunch = []')
ureg.define('head = []')
ureg.define('loaf = []')
ureg.define('package = []')
ureg.define('rib = []')


def get_staple_ingredients(html):
    soup = bs4.BeautifulSoup(html, 'html5lib')
    staples_div = soup.find('div', attrs={'id': 'staple'})
    staples_list = staples_div.find('ul', attrs={'class': 'shopping-list'})
    staple_ingredients = [c.find_all('span')[-1].contents[0].lower()
                          .replace('*', '').split(', ')
                          for c in staples_list.find_all('li')]
    staples_combined = set(it.chain(*staple_ingredients))
    return sorted([(staple, [i + 1 for i, recipe_staples in
                             enumerate(staple_ingredients)
                             if staple in recipe_staples])
                   for staple in staples_combined])


def get_section_ingredients(html):
    '''
    Combine all section (i.e., grocery, meat, etc.) shopping lists into a
    single dataframe with imperial and metric quantities.
    '''
    soup = bs4.BeautifulSoup(html, 'html5lib')
    main_list_section = soup.find('section', id='main-list')
    list_sections = {list_i.attrs['id']: list_i
                     for list_i in
                     main_list_section.find_all('div', class_='list-section')}
    name_i, list_i = list_sections.items()[1]

    frames = []
    keys = []

    cre_ingredient = re.compile(r'^(?P<side_dish>\*)?(?P<name>.*)[ \xa0]'
                                r'\((?P<quantity>[^\)]+?)(,\xa0(?P<optional>optional))?\)$')

    for name_i, list_i in list_sections.items():
        shopping_list_i = list_i.find('ul', class_='shopping-list')
        ingredient_strs_i = [li.find('span',
                                     class_='item-details').contents[-1]
                             for li in
                             shopping_list_i.find_all('li', class_='list-item')
                             if 'hidden' not in li.attrs['class']]
        if not ingredient_strs_i:
            continue

        df_ingredients_i = pd.DataFrame([cre_ingredient.match(i).groupdict()
                                        for i in ingredient_strs_i
                                         if cre_ingredient.match(i)])
        df_ingredients_i.insert(2, 'quantity_imperial',
                                df_ingredients_i.quantity
                                .map(ureg.parse_expression))
        df_ingredients_i.insert(3, 'quantity_metric',
                                [q.to_base_units()
                                 if isinstance(q, ureg.Quantity) else q
                                 for q in df_ingredients_i.quantity_imperial])
        frames.append(df_ingredients_i)
        keys.append(name_i)

    df_ingredients = pd.concat(frames, keys=keys)
    df_ingredients.side_dish = (df_ingredients.side_dish == '*')
    df_ingredients.optional = (df_ingredients.optional == 'optional')
    return df_ingredients[['quantity', 'name', 'quantity_metric',
                           'quantity_imperial', 'optional', 'side_dish']]
