# {{ menu['title'] }} *({{ menu['store'] }}, {{ menu['date'] }}, {{ menu['servings'] }})*

## Ingredient preparation

{{ df_ingredients.sort_values(['ingredient', 'processing', 'meal']).dropna().set_index(['ingredient', 'processing'])[['quantity', 'unit', 'meal', 'dish']].to_html() }}

------------------------------------------------------------------------
{% for meal in menu['meals'] %}
## {{ meal['main_dish']['title'] }} *with {% for d in meal['side_dishes'] %}{% if loop.index0 %}, and {% endif %}{{ d['title'] }}{% endfor %}* ({{ meal['duration'] }})

{%- if meal['notes'] %}

### Notes
{% for note in meal['notes'] %}
 - {{ note }}
{%- endfor -%}
{% endif %}

### Nutrition

|          |
|----------|
{%- for i in meal['nutrition'] %}
|{{ i }}|
{%- endfor %}

### Main dish

#### Ingredients

|      |
|------|
{% for ingredient in meal['main_dish']['ingredients'] -%}
| {{ ingredient }}    |
{% endfor %}

#### Instructions

{% for instruction in meal['main_dish']['instructions'] -%}
 {{ loop.index }}. {{ instruction }}
{% endfor %}

{% for side_dish in meal['side_dishes'] -%}
### *{{ side_dish['title'] }}*

#### Ingredients

|      |
|------|
{% for ingredient in side_dish['ingredients'] -%}
| {{ ingredient }}    |
{% endfor %}

#### Instructions

{% for instruction in side_dish['instructions'] -%}
 {{ loop.index }}. {{ instruction }}
{% endfor %}

{%- endfor %}

### Meal ingredients

{{ df_ingredients.fillna('-').set_index('meal').loc[loop.index].set_index(['processing', 'ingredient']).sort_index()[['quantity', 'unit', 'dish']].dropna().to_html() }}

------------------------------------------------------------------------
{% endfor -%}

## Ingredients summary

{{ df_ingredients.sort_values(['ingredient', 'meal']).set_index(['ingredient', 'meal', 'dish'])[['quantity', 'unit']].to_html() }}
