# coding: utf-8
import re

import bs4
import pandas as pd

from . import ureg


def extract_shopping_list(shopping_list_html, csv=False):
    '''
    Returns
    -------
    pandas.DataFrame or str
        Table of ingredients.

        For example:

                   amount      category                       ingredient   meal side_dish
            0        1 oz         dairy                     feta cheese       2     False
            1        2 oz         dairy              low fat sour cream       1     False
            2        3 oz         dairy               mascarpone cheese       4     False
            3        3 oz         dairy     plain greek yogurt, low-fat       3     False
            4        1 oz         dairy        shredded parmesan cheese       4     False
            5        3 oz        frozen  frozen corn (fresh works, too)       1     False
            6        3 oz        frozen                     frozen peas       3     False
            7           3       grocery          burrito-size tortillas       1     False
            8        8 oz       grocery              canned black beans       1     False
            9       15 oz       grocery         canned cannellini beans       5      True
            10       2 oz       grocery                   chicken broth       5     False
            11       4 oz       grocery                      mild salsa       1     False
            12  1 package       grocery             naan (or flatbread)       3      True
            13       8 oz       grocery                      ziti pasta       4     False
            14     3/4 lb  meat-poultry          chicken breast tenders       1     False
            15     3/4 lb  meat-poultry                   ground turkey       3     False
            16     3/4 lb  meat-poultry                  turkey cutlets       5     False
            17    1 bunch       produce                       asparagus   multi     False
            18       1 lb       produce                   baby potatoes       2      True
            19       2 oz       produce                    baby spinach       5     False
            20     1 head       produce             cauliflower, small        3      True
            21    1 bunch       produce                   fresh parsley   multi      True
            22     1 bulb       produce                          garlic   multi     False
            23     1/2 lb       produce                     green beans       5      True
            24    1 bunch       produce                            kale       2      True
            25          2       produce                          lemons   multi     False
            26          1       produce                            lime       3     False
            27       3 oz       produce                       mushrooms       4     False
            28          2       produce                          onions   multi     False
            29  1 package       produce                       salad mix       1      True
            30          1       produce                         shallot       4     False
            31          1       produce                   summer squash       4      True
            32          2       produce                        tomatoes   multi     False
            33          1       produce                        zucchini       4      True
            34       1 lb       seafood  fresh fish fillets, any choice       2     False
            35        NaN        staple                           butter      2      True
            36        NaN        staple                   cumin (ground)      3     False
            37        NaN        staple                    dijon mustard      2      True
            38        NaN        staple                    garlic powder      5      True
            39        NaN        staple                        olive oil      1     False
            40        NaN        staple                     onion powder      5      True
            41        NaN        staple                  oregano (dried)      2     False
            42        NaN        staple                   salad dressing      1      True
            43        NaN        staple               toasted sesame oil      5     False
            44        NaN        staple                         turmeric      3     False
    '''
    soup = bs4.BeautifulSoup(shopping_list_html, 'html5lib')
    staple_ingredient_items = soup.select('section#menu-key div#staple > '
                                          'ul.shopping-list > li')

    df_staple_ingredients = (pd.DataFrame([(i + 1,
                                            ingredient.replace('*', '')
                                            .lower(), '*' in ingredient)
                                           for i, staple_ingredient_item_i in
                                           enumerate(staple_ingredient_items)
                                           for ingredient in
                                           re.split(r',\s*',
                                                    staple_ingredient_item_i
                                                    .select('span')[-1]
                                                    .contents[0])],
                                          columns=['meal', 'ingredient',
                                                   'side_dish'])
                             .drop_duplicates('ingredient'))
    df_staple_ingredients.insert(0, 'category', 'staple')

    ingredient_items = soup.select('section#main-list div > div.list-section >'
                                   ' ul.shopping-list > li.list-item')

    df_ingredients = pd.DataFrame(map(extract_ingredient, ingredient_items),
                                  columns=['meal', 'category', 'ingredient',
                                           'side_dish'])
    df_ingredients.dropna(inplace=True)
    df_ingredients = df_ingredients.join(df_ingredients.ingredient.str
                                         .extract(r'^(?P<name>.*?)\s*'
                                                  r'\((?P<quantity>[^\)]+)\)$',
                                                  expand=False))
    df_ingredients.name = df_ingredients.name.str.lower()
    df_ingredients.drop('ingredient', axis=1, inplace=True)
    df_ingredients.rename(columns={'name': 'ingredient'}, inplace=True)
    df_ingredients = pd.concat([df_staple_ingredients, df_ingredients])
    df_ingredients.sort_values(['category', 'ingredient', 'meal'], inplace=True)
    df_ingredients.reset_index(inplace=True, drop=True)

    # df_ingredients.insert(2, 'quantity_imperial',
                          # df_ingredients.quantity.astype(str)
                          # .map(ureg.parse_expression))
    # df_ingredients.insert(3, 'quantity_metric',
                          # [q.to_base_units() if isinstance(q, ureg.Quantity)
                           # else q for q in df_ingredients.quantity_imperial])

    if csv:
        return df_ingredients.to_csv(index=False, encoding='utf8')
    else:
        return df_ingredients


def extract_ingredient(ingredient_item):
    category_i = ingredient_item.find_parent('div').attrs['id']

    for i in range(1, 6) + ['multi']:
        if u'list-%s' % i in ingredient_item.attrs['class']:
            meal_i = i
            break
    else:
        meal_i = None
    name_i = ingredient_item.select('span')[3].contents[0] if meal_i else None
    if name_i is not None:
        side_dish_i = '*' in name_i
        name_i = name_i.replace('*', '')
    else:
        side_dish_i = None
    return (meal_i, category_i, name_i, side_dish_i)
