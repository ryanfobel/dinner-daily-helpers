from __future__ import print_function, unicode_literals, division
import argparse
import io
import json
import os
import subprocess as sp
import sys

import jinja2
import pandas as pd

from .menu import extract_menu, ingredients_table


PARENT_DIR = os.path.realpath(os.path.join(__file__, os.path.pardir))


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('weekly_menu_html', help='Weekly menu HTML document.')
    parser.add_argument('output_path', default='-', help='Output path '
                        '(default: write to `stdout`)', nargs='?')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--markdown', action='store_true')

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    with open(args.weekly_menu_html, 'r') as input_:
        menu_html = input_.read()

    menu = extract_menu(menu_html)

    if args.json:
        # Dump as JSON output.
        if args.output_path == '-':
            output = sys.stdout
        else:
            output = open(args.output_path, 'w')

        try:
            json.dump(menu, output, indent=4, sort_keys=True)
        finally:
            if args.output_path != '-':
                output.close()
    else:
        menu_markdown = io.StringIO()
        template_path = os.path.join(PARENT_DIR, 'weekly_menu.template.md')
        with open(template_path, 'r') as input_:
            template = jinja2.Template(input_.read())

        df_ingredients = ingredients_table(menu)

        print(template.render(menu=menu, df_ingredients=df_ingredients),
              file=menu_markdown)

        if args.markdown:
            # Dump as markdown.
            if args.output_path == '-':
                print(menu_markdown.getvalue(), end='')
            else:
                with open(args.output_path, 'w') as output:
                    output.write(menu_markdown.getvalue().encode('utf8'))
        else:
            # Dump as HTML.
            p = sp.Popen('pandoc -f gfm -t html - --template GitHub.html5',
                         stdout=sp.PIPE, stdin=sp.PIPE)
            p.stdin.write(menu_markdown.getvalue().encode('utf8'))
            stdout, stderr = p.communicate()

            if args.output_path == '-':
                print(stdout.strip())
            else:
                with open(args.output_path, 'w') as output:
                    output.write(stdout)
