from jinja2.runtime import LoopContext, Macro, Markup, Namespace, TemplateNotFound, TemplateReference, TemplateRuntimeError, Undefined, escape, identity, internalcode, markup_join, missing, str_join
name = 'base.html'

def root(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    l_0_url_for = resolve('url_for')
    pass
    yield '<!DOCTYPE html>\n<html lang="en">\n  <head>\n    <meta charset="utf-8" />\n    <meta name="viewport" content="width=device-width, initial-scale=1" />\n    <title>'
    yield from context.blocks['title'][0](context)
    yield '</title>\n    <link rel="preconnect" href="https://fonts.googleapis.com" />\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n    <link\n      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Outfit:wght@400;500;600;700&display=swap"\n      rel="stylesheet"\n    />\n    <link rel="stylesheet" href="'
    yield escape(context.call((undefined(name='url_for') if l_0_url_for is missing else l_0_url_for), 'static', filename='style.css'))
    yield '" />\n    '
    yield from context.blocks['extra_head'][0](context)
    yield '\n  </head>\n  <body>\n    <div class="ambient" aria-hidden="true">\n      <div class="orb orb-a"></div>\n      <div class="orb orb-b"></div>\n      <div class="orb orb-c"></div>\n      <div class="grain" aria-hidden="true"></div>\n    </div>\n\n    <div class="wrap '
    yield from context.blocks['wrap_class'][0](context)
    yield '">\n      <header class="top">\n        <a href="'
    yield escape(context.call((undefined(name='url_for') if l_0_url_for is missing else l_0_url_for), 'index'))
    yield '" class="brand brand-link" title="Home">\n          <span class="brand-mark" aria-hidden="true"></span>\n          <span class="brand-text">Financial Market <span class="brand-accent">Insights</span></span>\n        </a>\n        <span class="live-pill">\n          <span class="live-dot"></span>\n          yfinance\n        </span>\n      </header>\n\n      '
    yield from context.blocks['content'][0](context)
    yield '\n\n      <footer class="foot">\n        <p>For research only — not investment advice.</p>\n      </footer>\n    </div>\n  </body>\n</html>'

def block_title(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    pass
    yield 'Financial Market Insights'

def block_extra_head(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    pass

def block_wrap_class(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    pass

def block_content(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    pass

blocks = {'title': block_title, 'extra_head': block_extra_head, 'wrap_class': block_wrap_class, 'content': block_content}
debug_info = '6=13&13=15&14=17&24=19&26=21&36=23&6=26&14=36&24=45&36=54'