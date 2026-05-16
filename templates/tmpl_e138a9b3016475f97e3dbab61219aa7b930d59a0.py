from jinja2.runtime import LoopContext, Macro, Markup, Namespace, TemplateNotFound, TemplateReference, TemplateRuntimeError, Undefined, escape, identity, internalcode, markup_join, missing, str_join
name = 'ticker.html'

def root(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    parent_template = None
    pass
    parent_template = environment.get_template('base.html', 'ticker.html')
    for name, parent_block in parent_template.blocks.items():
        context.blocks.setdefault(name, []).append(parent_block)
    yield from parent_template.root_render_func(context)

def block_title(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    l_0_error = resolve('error')
    l_0_name = resolve('name')
    l_0_symbol = resolve('symbol')
    pass
    yield '\n  '
    if (undefined(name='error') if l_0_error is missing else l_0_error):
        pass
        yield 'Financial Market Insights'
    else:
        pass
        yield escape(((undefined(name='name') if l_0_name is missing else l_0_name) or (undefined(name='symbol') if l_0_symbol is missing else l_0_symbol)))
        yield ' — Financial Market Insights'
    yield '\n'

def block_wrap_class(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    pass
    yield 'wrap--ticker'

def block_extra_head(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    l_0_url_for = resolve('url_for')
    pass
    yield '\n  <script\n    src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"\n    defer\n  ></script>\n  <script src="'
    yield escape(context.call((undefined(name='url_for') if l_0_url_for is missing else l_0_url_for), 'static', filename='ticker_page.js', _block_vars=_block_vars))
    yield '" defer></script>\n'

def block_content(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    l_0_url_for = resolve('url_for')
    l_0_error = resolve('error')
    l_0_market_display = resolve('market_display')
    l_0_name = resolve('name')
    l_0_symbol = resolve('symbol')
    l_0_exchange = resolve('exchange')
    l_0_currency = resolve('currency')
    l_0_last_display = resolve('last_display')
    l_0_change_percent = resolve('change_percent')
    l_0_interval = resolve('interval')
    l_0_analysis_sections = resolve('analysis_sections')
    l_0_graph_series = resolve('graph_series')
    try:
        t_1 = environment.filters['e']
    except KeyError:
        @internalcode
        def t_1(*unused):
            raise TemplateRuntimeError("No filter named 'e' found.")
    try:
        t_2 = environment.filters['format']
    except KeyError:
        @internalcode
        def t_2(*unused):
            raise TemplateRuntimeError("No filter named 'format' found.")
    try:
        t_3 = environment.filters['tojson']
    except KeyError:
        @internalcode
        def t_3(*unused):
            raise TemplateRuntimeError("No filter named 'tojson' found.")
    try:
        t_4 = environment.tests['none']
    except KeyError:
        @internalcode
        def t_4(*unused):
            raise TemplateRuntimeError("No test named 'none' found.")
    pass
    yield '\n  <nav class="crumb">\n    <a href="'
    yield escape(context.call((undefined(name='url_for') if l_0_url_for is missing else l_0_url_for), 'index', _block_vars=_block_vars))
    yield '" class="crumb-link">← Home</a>\n  </nav>\n\n  '
    if (undefined(name='error') if l_0_error is missing else l_0_error):
        pass
        yield '\n    <div class="panel alert-panel">\n      <p class="alert-msg">'
        yield escape((undefined(name='error') if l_0_error is missing else l_0_error))
        yield '</p>\n      <a href="'
        yield escape(context.call((undefined(name='url_for') if l_0_url_for is missing else l_0_url_for), 'index', _block_vars=_block_vars))
        yield '" class="btn secondary btn-inline">Back to search</a>\n    </div>\n  '
    else:
        pass
        yield '\n    <section class="ticker-hero panel">\n      <div class="ticker-hero-row">\n        <div>\n          <span class="market-badge">'
        yield escape((undefined(name='market_display') if l_0_market_display is missing else l_0_market_display))
        yield '</span>\n          <h1 class="ticker-title">'
        yield escape(((undefined(name='name') if l_0_name is missing else l_0_name) or (undefined(name='symbol') if l_0_symbol is missing else l_0_symbol)))
        yield '</h1>\n          <p class="ticker-meta">\n            <span class="mono">'
        yield escape((undefined(name='symbol') if l_0_symbol is missing else l_0_symbol))
        yield '</span>\n            '
        if (undefined(name='exchange') if l_0_exchange is missing else l_0_exchange):
            pass
            yield '<span class="dot-sep">·</span> '
            yield escape((undefined(name='exchange') if l_0_exchange is missing else l_0_exchange))
        yield '\n            '
        if (undefined(name='currency') if l_0_currency is missing else l_0_currency):
            pass
            yield '<span class="dot-sep">·</span> '
            yield escape((undefined(name='currency') if l_0_currency is missing else l_0_currency))
        yield '\n          </p>\n        </div>\n        <div class="ticker-price-block">\n          '
        if (undefined(name='last_display') if l_0_last_display is missing else l_0_last_display):
            pass
            yield '\n            <span class="price-label">Last</span>\n            <div class="q-price ticker-page-price" id="display-last">'
            yield escape((undefined(name='last_display') if l_0_last_display is missing else l_0_last_display))
            yield '</div>\n          '
        yield '\n          '
        if (not t_4((undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent))):
            pass
            yield '\n            <div\n              class="chip q-change '
            if ((undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent) > 0):
                pass
                yield 'up'
            elif ((undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent) < 0):
                pass
                yield 'down'
            else:
                pass
                yield 'neutral'
            yield '"\n              id="display-change"\n            >\n              '
            if ((undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent) > 0):
                pass
                yield '▲ +'
            elif ((undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent) < 0):
                pass
                yield '▼ '
            yield escape(t_2('%.2f', (undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent)))
            yield '%\n            </div>\n          '
        elif (t_4((undefined(name='change_percent') if l_0_change_percent is missing else l_0_change_percent)) and (undefined(name='last_display') if l_0_last_display is missing else l_0_last_display)):
            pass
            yield '\n            <div class="chip q-change neutral" id="display-change">—</div>\n          '
        yield '\n        </div>\n      </div>\n    </section>\n\n    <article class="panel chart-panel ticker-chart-panel">\n      <div class="chart-head">\n        <div>\n          <h2 class="section-title">Chart</h2>\n          <p class="section-sub">\n            Closing price grouped by the selected interval.\n          </p>\n        </div>\n        <div class="chart-controls">\n          <label class="label chart-label" for="interval">View by</label>\n          <div class="input-shell input-shell--select">\n            <select id="interval" name="interval">\n              <option value="day" '
        if ((undefined(name='interval') if l_0_interval is missing else l_0_interval) == 'day'):
            pass
            yield 'selected'
        yield '>Day</option>\n              <option value="week" '
        if ((undefined(name='interval') if l_0_interval is missing else l_0_interval) == 'week'):
            pass
            yield 'selected'
        yield '>Week</option>\n              <option value="month" '
        if ((undefined(name='interval') if l_0_interval is missing else l_0_interval) == 'month'):
            pass
            yield 'selected'
        yield '>Month</option>\n              <option value="quarter" '
        if ((undefined(name='interval') if l_0_interval is missing else l_0_interval) == 'quarter'):
            pass
            yield 'selected'
        yield '>Quarter</option>\n              <option value="year" '
        if ((undefined(name='interval') if l_0_interval is missing else l_0_interval) == 'year'):
            pass
            yield 'selected'
        yield '>Year</option>\n            </select>\n          </div>\n        </div>\n      </div>\n      <div class="chart-wrap chart-wrap--ticker">\n        <canvas id="template-chart" height="140"></canvas>\n      </div>\n    </article>\n\n    <section class="analysis-section">\n      <h2 class="section-title analysis-heading">Analysis</h2>\n      <p class="section-sub analysis-lead">\n        Quant and fundamentals snapshot generated from recent price history and Yahoo Finance metadata.\n      </p>\n      <div class="analysis-grid">\n        '
        for l_1_block in (undefined(name='analysis_sections') if l_0_analysis_sections is missing else l_0_analysis_sections):
            _loop_vars = {}
            pass
            yield '\n          '
            if environment.getattr(l_1_block, 'hidden'):
                pass
                yield '\n            \n            '
                if environment.getattr(l_1_block, 'markers'):
                    pass
                    yield '\n              <script type="application/json" id="ticker-markers-json">\n                '
                    yield escape(t_3(context.eval_ctx, environment.getattr(l_1_block, 'markers')))
                    yield '\n              </script>\n            '
                yield '\n          '
            else:
                pass
                yield '\n            <article class="panel analysis-card">\n              <div class="analysis-card-head">\n                <h3 class="analysis-card-title">'
                yield escape(environment.getattr(l_1_block, 'title'))
                yield '</h3>\n                '
                if environment.getattr(l_1_block, 'metric_label'):
                    pass
                    yield '\n                  <span class="analysis-metric">\n                    <span class="analysis-metric-label">'
                    yield escape(environment.getattr(l_1_block, 'metric_label'))
                    yield '</span>\n                    <span class="analysis-metric-value">'
                    yield escape(environment.getattr(l_1_block, 'metric_value'))
                    yield '</span>\n                  </span>\n                '
                yield '\n              </div>\n              <p class="analysis-card-body">'
                yield escape(environment.getattr(l_1_block, 'body'))
                yield '</p>\n              '
                if environment.getattr(l_1_block, 'links'):
                    pass
                    yield '\n                <ul class="analysis-links">\n                  '
                    for l_2_link in environment.getattr(l_1_block, 'links'):
                        _loop_vars = {}
                        pass
                        yield '\n                    <li>\n                      <a href="'
                        yield escape(t_1(environment.getattr(l_2_link, 'url')))
                        yield '" target="_blank" rel="noopener noreferrer">\n                        '
                        yield escape(environment.getattr(l_2_link, 'title'))
                        yield '\n                      </a>\n                      '
                        if environment.getattr(l_2_link, 'meta'):
                            pass
                            yield '<span class="analysis-link-meta">'
                            yield escape(environment.getattr(l_2_link, 'meta'))
                            yield '</span>'
                        yield '\n                    </li>\n                  '
                    l_2_link = missing
                    yield '\n                </ul>\n              '
                yield '\n            </article>\n          '
            yield '\n        '
        l_1_block = missing
        yield '\n      </div>\n    </section>\n\n    <script type="application/json" id="ticker-chart-data">\n      '
        yield escape(t_3(context.eval_ctx, (undefined(name='graph_series') if l_0_graph_series is missing else l_0_graph_series)))
        yield '\n    </script>\n    <script type="application/json" id="ticker-meta-json">\n      '
        yield escape(t_3(context.eval_ctx, {'currency': ((undefined(name='currency') if l_0_currency is missing else l_0_currency) or 'USD')}))
        yield '\n    </script>\n  '
    yield '\n'

blocks = {'title': block_title, 'wrap_class': block_wrap_class, 'extra_head': block_extra_head, 'content': block_content}
debug_info = '1=12&3=17&4=29&7=38&9=48&14=58&17=61&19=106&22=108&24=111&25=113&31=118&32=120&34=122&35=124&36=129&40=134&42=137&44=140&46=143&49=153&51=161&70=165&71=169&72=173&73=177&74=181&90=185&91=189&93=192&95=195&101=201&102=203&104=206&105=208&109=211&110=213&112=216&114=220&115=222&117=224&129=236&132=238'