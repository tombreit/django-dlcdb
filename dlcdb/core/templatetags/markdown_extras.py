from django import template
from django.template.defaultfilters import stringfilter

import markdown

register = template.Library()


@register.filter
@stringfilter
def from_markdown(value):

    config = {
        # 'smarty': [
        #     ('smart_angled_quotes', True),
        #     ('substitutions', {
        #         'ndash': '\u2013',
        #         'mdash': '\u2014',
        #         'ellipsis': '\u2026',
        #         'left-single-quote': '&sbquo;',  # sb is not a typo!
        #         'right-single-quote': '&lsquo;',
        #         'left-double-quote': '&bdquo;',
        #         'right-double-quote': '&ldquo;',
        #         'left-angle-quote': '[',
        #         'right-angle-quote': ']',
        #     }),
        # ]
    }

    md = markdown.Markdown(
        extensions=[
            'smarty',
            'fenced_code',
            'admonition',
        ],
        extension_configs=config,
    )

    html = md.convert(value)
    html = html.replace("[ ]", "<input type='checkbox'>")

    return html
