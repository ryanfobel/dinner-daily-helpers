from __future__ import print_function, unicode_literals, division
import io
import itertools as it
import re
import os
import json

import bs4
import pandas as pd
import pint
import six
import requests

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
                     .select('div.dishes > div.side-dishes > div.details')
                     if dish_div_ij.select_one('h5.side-heading > span.label')
                     .contents[0].lower() != 'add a side']

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
    try:
        # Parse title, store, date, and servings from menus up until 2019-03-17
        result = dict(zip(['store', 'date', 'servings'],
                          [s.strip() for s in soup.select_one('header > h2')
                           .contents[0].split('-')]))
        result['title'] = soup.select_one('header > h1').contents[0].strip()
    except AttributeError:
        try:
            # Parse title, store, date, and servings from menus after 2019-03-17
            result = {}
            result['title'] = soup.select_one('header div#family-label > '
                                            'h1').text.strip()
            result['date'] = soup.select_one('header .theme-date').text.split('-')[-1].strip()
            result['store'] = soup.select_one('header .theme-store-name').text
            result['servings'] = soup.select_one('header div#family-label > h2').text
        except Exception:
            import pdb; pdb.set_trace()  # XXX BREAKPOINT
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
                                              r'((?P<unit>\S+)\s+)?'
                                              r'(?P<description>\S+.*?)'
                                              r'(,\s+divided)?$',
                                              expand=False)
    # Drop implied unnamed groups: 1) from `quantity` named group, and 2) from
    # `", divided"`.
    df_decode_ingredients.drop([1, 2, 5], axis=1, inplace=True)

    isna = df_decode_ingredients['quantity'].isna()
    df_decode_ingredients.loc[isna, 'description'] =\
        df_ingredients['ingredient']
    df_decode_ingredients.loc[isna, 'quantity'] = 1

    # Set unit to `"each"` for ingredients where no units were specified.
    for i, ingredient_i in df_decode_ingredients.iterrows():
        (quantity_i, unit_i, desc_i) = ingredient_i
        try:
            ureg.parse_expression('%s %s' % (quantity_i, unit_i))
        except pint.UndefinedUnitError:
            # No recognized unit.  Assume unit is omitted, and assume "each".
            if unit_i == unit_i and isinstance(unit_i, six.string_types):
                desc_i = '%s %s' % (unit_i, desc_i)
            unit_i = 'each'
            ingredient_i.description = desc_i
            ingredient_i.unit = unit_i

    # Extract any processing instructions.
    actions = ['chopped', 'peeled', 'minced', 'diced', 'sliced', 'drained',
               'rinsed', 'ends trimmed', 'shredded']
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


def convert_recipe_to_json_ld(recipe, category='Entree', yield_='2-3 people'):
    baseurl = 'https://db.thedinnerdaily.com'

    url = '%s/recipes/%s' % (baseurl, 
        re.sub('[-]+', '-', re.sub(r'[&|,| ]', '-', recipe['title'].lower())))
    response = requests.get(url)
    soup = bs4.BeautifulSoup(response.content, 'html5lib')
    
    result = {
          "@context": "https://schema.org/",
          "@type": "Recipe",
          "name": recipe['title'],
          "url": url,
          "author": {
            "@type": "Organization",
            "name": "The Dinner Daily",
            "recipeCategory": category,
          },
    }

    img = soup.find('img', class_='recipe-image')
    if img:
        result['image'] = [baseurl + size.split(' ')[0] for size in img['srcset'].split(', ')]

    duration = soup.find('span', class_='duration').text

    # Convert to ISO_8601 format (https://en.wikipedia.org/wiki/ISO_8601)
    result['totalTime'] = 'PT%sM' % re.search('(?P<min>\d+) MINS', duration).groupdict()['min']

    result['recipeYield'] = yield_
    result['recipeIngredient'] = recipe['ingredients']
    result['recipeInstructions'] = [{"@type": "HowToStep",
                                      #"name": "Enjoy",
                                      "text": step,
                                      #"url": "https://example.com/party-coffee-cake#step6",
                                      #"image": "https://example.com/photos/party-coffee-cake/step6.jpg"
                                     } for step in recipe['instructions']]
    
    nutrition = [li.contents[0] for li in soup.find('ul', class_='nutrition').select('li')]
    nutrition = dict(item.split(' ', maxsplit=1)[::-1] for item in nutrition)
    nutrition = {k.lower(): v for k, v in nutrition.items()}

    rename_fields = { 'protein': 'proteinContent',
                      'fiber': 'fiberContent',
                      'carbs': 'carbohydrateContent',
                      'saturated fat': 'saturatedFatContent',
                      'sodium': 'sodiumContent',
                      'cals': 'calories',
                      'fat': 'fatContent',
    }

    for k, v in rename_fields.items():
        nutrition[v] = nutrition.pop(k)
        match = re.search('(?P<value>\d+)(?P<units>.*)', nutrition[v])
        value, units = match.groups()
        value = float(value)
        if units == 'mg':
            value /= 1e3
            units = 'g'
        if v == 'calories':
            value /= 1e3
            units = 'calories'
        nutrition[v] = '%s %s' % (value, units)

    result['nutrition'] = nutrition    
    
    result["discussionUrl"] = result['url']
    return result


def extract_recipes_from_menu(menu):
    recipes = {}
    for meal in menu['meals']:
        json_ld = convert_recipe_to_json_ld(meal['main_dish'])
        recipes[json_ld['name']] = json_ld

        for side in meal['side_dishes']:
            json_ld = convert_recipe_to_json_ld(side, 'Side')
            recipes[json_ld['name']] = json_ld
    return recipes


def export_json_ld(recipe, output_directory):
    os.makedirs(output_directory, exist_ok=True)
    with open(os.path.join(output_directory, recipe['url'].split('/')[-1] + '.json'), 'w') as f:
        json.dump(recipe, f, indent=4)
    
    # export images
    if 'image' in recipe.keys():
        image_dir = os.path.join(output_directory, 'images', recipe['url'].split('/')[-1])

        for url in recipe['image']:
            os.makedirs(image_dir, exist_ok=True)
            filepath = os.path.join(image_dir, url.split('/')[-1])
            r = requests.get(url, allow_redirects=True)
            open(filepath, 'wb').write(r.content)        
