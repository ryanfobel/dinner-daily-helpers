from __future__ import print_function, unicode_literals, division
import io
import itertools as it
import re

import bs4
import pandas as pd
import pint

from . import ureg


def dish_to_markdown(dish):
    output = io.StringIO()

    print('# %s' % dish['title'], file=output)
    print('', file=output)

    # Write ingredients list as Markdown table.
    ingredients_ij = dish['ingredients']
    ingredients_count_ij = len(ingredients_ij)
    left_ij = ingredients_ij[:ingredients_count_ij // 2]
    right_ij = ingredients_ij[ingredients_count_ij // 2:]

    print('## Ingredients', file=output)
    print('', file=output)
    print('| |', file=output)
    print('|------|------|', file=output)

    for left, right in it.izip_longest(left_ij, right_ij):
        if left is not None:
            print('| %s | %s |' % (left, right), file=output)
        else:
            print('| %s |    |' % right, file=output)
    print('', file=output)

    print('## Instructions', file=output)
    print('', file=output)
    instructions_i = [' %d. %s' % (i + 1, instruction)
                      for i, instruction in enumerate(dish['instructions'])]
    print('\n'.join(instructions_i), file=output)
    return output.getvalue().strip()


def extract_meal(meal_div):
    # Duration
    duration_i = meal_div.find('span', class_='duration').contents[0]

    # Main dish title
    title_i = meal_div.select_one('h3 span.label').contents[0]

    def extract_recipe(recipe_div):
        recipe = {}

        # ## Title
        title_span = recipe_div.select_one('h5 > span.label')
        if title_span is not None:
            recipe['title'] = title_span.contents[0]

        # ## Ingredients
        recipe['ingredients'] = [li.contents[0]
                                 for li in recipe_div.select('li')]

        # ## Instructions
        recipe['instructions'] = re.sub(r'\.\s+', '.\n',
                                        recipe_div
                                        .select_one('div.instructions p')
                                        .contents[0]).splitlines()
        return recipe

    # Main dish
    main_dish_div_i = meal_div.select_one('div.dishes > div.details')
    main_dish_i = extract_recipe(main_dish_div_i)
    main_dish_i['title'] = title_i

    # Side dishes
    side_dishes_i = [extract_recipe(dish_div_ij) for dish_div_ij in meal_div
                     .select('div.dishes > div.side-dishes > div.details')]

    # Meal nutrition
    nutrition_i = [li.contents[0]
                   for li in meal_div.select('ul.nutrition > li')]

    meal = {'main_dish': main_dish_i,
            'side_dishes': side_dishes_i,
            'duration': duration_i,
            'nutrition': nutrition_i}

    # Meal notes
    notes_div_i = meal_div.find('div', class_='recipe-notes')
    if notes_div_i is not None:
        meal['notes'] = [p.contents[0] for p in notes_div_i.select('p')]
    return meal


def extract_menu(weekly_html):
    soup = bs4.BeautifulSoup(weekly_html, 'html5lib')
    result = dict(zip(['store', 'date', 'servings'],
                      [s.strip() for s in soup.select_one('header > h2')
                       .contents[0].split('-')]))
    result['title'] = soup.select_one('header > h1').contents[0].strip()
    menu_list = soup.find('ul', id='menu')
    meal_items = menu_list.find_all('li', id=re.compile('item-\d+'))
    result['meals'] = [extract_meal(meal_div_i) for meal_div_i in meal_items]
    return result


def ingredients_table(menu, decode_processing=True):
    '''
    Parameters
    ----------
    menu : dict
        Menu in format returned by :func:`extract_menu`.

    Returns
    -------
    pandas.DataFrame
        Table with the following columns: [u'meal', u'dish', u'ingredient',
        u'side']

        For example:

               meal                     dish                          ingredient   side
            0     0  Southwest Chicken Wraps       3/4 lb chicken breast tenders  False
            1     0  Southwest Chicken Wraps                     1 tbs olive oil  False
            2     0  Southwest Chicken Wraps           1/4 onion, small, chopped  False
            3     0  Southwest Chicken Wraps                 1/2 cup frozen corn  False
            4     0  Southwest Chicken Wraps  8 oz black beans, drained & rinsed  False

        If :data:`decode_processing` is ``True``, decode ingredient into
        quantity, units, and processing, e.g.:

               meal                     dish   side quantity  unit              ingredient        processing
            0     0  Southwest Chicken Wraps  False      3/4    lb  chicken breast tenders               NaN
            1     0  Southwest Chicken Wraps  False        1   tbs               olive oil               NaN
            2     0  Southwest Chicken Wraps  False      1/4  each            onion, small           chopped
            3     0  Southwest Chicken Wraps  False      1/2   cup             frozen corn               NaN
            4     0  Southwest Chicken Wraps  False        8    oz             black beans  drained & rinsed
    '''
    ingredients = []

    for i, meal_i in enumerate(menu['meals']):
        main_name_i = meal_i['main_dish']['title']
        ingredients += [(i + 1, main_name_i, ingredient, False)
                        for ingredient in
                        meal_i['main_dish']['ingredients']]
        for j, side_ij in enumerate(meal_i['side_dishes']):
            ingredients += [(i + 1, side_ij['title'], ingredient, True)
                            for ingredient in side_ij['ingredients']]
    df_ingredients = pd.DataFrame(ingredients, columns=['meal', 'dish',
                                                        'ingredient',
                                                        'side'])

    if not decode_processing:
        return df_ingredients

    df_decode_ingredients = \
        df_ingredients.ingredient.str.extract(r'^(?P<quantity>[\d\/]+'
                                              r'(\s+[\d\/]+)?)\s+'
                                              r'(?P<unit>\S+)\s+'
                                              r'(?P<description>\S+.*?)'
                                              r'(,\s+divided)?$',
                                              expand=False)
    # Drop implied unnamed groups: 1) from `quantity` named group, and 2) from
    # `", divided"`.
    df_decode_ingredients.drop([1, 4], axis=1, inplace=True)

    # Set unit to `"each"` for ingredients where no units were specified.
    for i, ingredient_i in df_decode_ingredients.iterrows():
        (quantity_i, unit_i, desc_i) = ingredient_i
        try:
            ureg.parse_expression('%s %s' % (quantity_i, unit_i))
        except pint.UndefinedUnitError:
            # No recognized unit.  Assume unit is omitted, and assume "each".
            desc_i = unit_i + ' ' + desc_i
            unit_i = 'each'
            ingredient_i.description = desc_i
            ingredient_i.unit = unit_i

    # Extract any processing instructions.
    actions = ['chopped', 'minced', 'diced', 'sliced', 'drained', 'rinsed']
    df_processing = (df_decode_ingredients.description.str
                     .extract(r'(?P<root>.*?)'
                              r'(,\s+(?P<processing>[^,]*(%s)[^,]*))?$'
                              % '|'.join(actions), expand=True)[['root',
                                                                 'processing']])
    df_decode_ingredients['description'] = df_processing['root']
    df_decode_ingredients['processing'] = df_processing['processing']

    df_decode_ingredients = df_ingredients.join(df_decode_ingredients)
    df_decode_ingredients.drop('ingredient', axis=1, inplace=True)
    df_decode_ingredients.rename(columns={'description': 'ingredient'},
                                 inplace=True)
    return df_decode_ingredients
