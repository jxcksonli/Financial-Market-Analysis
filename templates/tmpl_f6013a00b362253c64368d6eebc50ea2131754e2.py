from jinja2.runtime import LoopContext, Macro, Markup, Namespace, TemplateNotFound, TemplateReference, TemplateRuntimeError, Undefined, escape, identity, internalcode, markup_join, missing, str_join
name = 'index.html'

def root(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    parent_template = None
    pass
    parent_template = environment.get_template('base.html', 'index.html')
    for name, parent_block in parent_template.blocks.items():
        context.blocks.setdefault(name, []).append(parent_block)
    yield from parent_template.root_render_func(context)

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
    yield escape(context.call((undefined(name='url_for') if l_0_url_for is missing else l_0_url_for), 'static', filename='home.js', _block_vars=_block_vars))
    yield '" defer></script>\n'

def block_content(context, missing=missing):
    resolve = context.resolve_or_missing
    undefined = environment.undefined
    concat = environment.concat
    cond_expr_undefined = Undefined
    if 0: yield None
    _block_vars = {}
    pass
    yield '\n  <section class="hero">\n    <h1 class="hero-title">Look up any ticker</h1>\n    <p class="hero-lead">\n      US equities (NYSE / NASDAQ) or Australian listings on the ASX. For ASX, you can type\n      <span class="kbd">BHP</span> — we append <span class="kbd">.AX</span> when needed.\n    </p>\n  </section>\n\n  <form id="lookup-form" class="panel form-panel" autocomplete="off" action="#" method="get">\n    <div class="form-grid">\n      <label class="field field-grow">\n        <span class="label">Symbol</span>\n        <div class="input-shell">\n          <input\n            type="text"\n            id="ticker"\n            name="ticker"\n            placeholder="AAPL, MSFT, BHP…"\n            maxlength="32"\n            spellcheck="false"\n            autocomplete="off"\n            required\n          />\n        </div>\n      </label>\n\n      <fieldset class="market-fieldset">\n        <legend class="label">Market</legend>\n        <div class="market-options">\n          <label class="tile">\n            <input type="radio" name="market" value="us" checked />\n            <span class="tile-body">\n              <span class="tile-title">United States</span>\n              <span class="tile-sub">NYSE · NASDAQ</span>\n            </span>\n          </label>\n          <label class="tile">\n            <input type="radio" name="market" value="asx" />\n            <span class="tile-body">\n              <span class="tile-title">Australia</span>\n              <span class="tile-sub">ASX · ASX 200</span>\n            </span>\n          </label>\n        </div>\n      </fieldset>\n    </div>\n\n    <button type="submit" class="btn primary" id="submit-btn">\n      <span class="btn-label">Open insight page</span>\n    </button>\n  </form>\n\n  <section class="panel watchlist-panel" aria-label="Watchlist comparison chart">\n    <div class="chart-head">\n      <div>\n        <h2 class="section-title">Watchlist chart</h2>\n        <p class="section-sub">\n          Add multiple tickers and track them together on one graph.\n        </p>\n      </div>\n      <div class="chart-controls">\n        <label class="label chart-label" for="watch-interval">View by</label>\n        <div class="input-shell input-shell--select">\n          <select id="watch-interval" name="interval">\n            <option value="day">Day</option>\n            <option value="week">Week</option>\n            <option value="month">Month</option>\n            <option value="quarter">Quarter</option>\n            <option value="year">Year</option>\n          </select>\n        </div>\n      </div>\n      <div class="chart-controls">\n        <label class="label chart-label" for="watch-scale">Display</label>\n        <div class="input-shell input-shell--select">\n          <select id="watch-scale" name="scale">\n            <option value="pct" selected>% Change</option>\n            <option value="price">Price</option>\n          </select>\n        </div>\n      </div>\n    </div>\n\n    <div class="watchlist-controls">\n      <label class="field field-grow">\n        <span class="label">Add ticker</span>\n        <div class="input-shell">\n          <input\n            type="text"\n            id="watch-ticker"\n            placeholder="AAPL, MSFT, BHP…"\n            maxlength="32"\n            spellcheck="false"\n            autocomplete="off"\n          />\n        </div>\n      </label>\n      <button type="button" class="btn secondary btn-inline" id="watch-add-btn">Add</button>\n      <button type="button" class="btn secondary btn-inline" id="watch-clear-btn">Clear</button>\n    </div>\n\n    <div class="watchlist-chips" id="watchlist-chips" aria-live="polite"></div>\n    <p class="status" id="watch-status"></p>\n\n    <div class="chart-wrap">\n      <canvas id="watchlist-chart" height="140"></canvas>\n    </div>\n\n    <div class="watchlist-table-wrap" aria-label="Watchlist summary table">\n      <table class="watch-table">\n        <thead>\n          <tr>\n            <th>Ticker</th>\n            <th class="num">Last</th>\n            <th class="num">1D</th>\n            <th class="num">1W</th>\n            <th class="num">1M</th>\n            <th>Trend</th>\n          </tr>\n        </thead>\n        <tbody id="watchlist-tbody"></tbody>\n      </table>\n    </div>\n  </section>\n'

blocks = {'extra_head': block_extra_head, 'content': block_content}
debug_info = '1=12&3=17&8=27&11=30'