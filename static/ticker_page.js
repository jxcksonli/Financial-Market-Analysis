(function () {
  const app = document.getElementById("chart-app");
  if (!app || typeof Plotly === "undefined") return;

  const DEFAULT_WATCHLIST = [
    { label: "NDQ", ticker: "NDQ", market: "asx" },
    { label: "VAS", ticker: "VAS", market: "asx" },
    { label: "VGS", ticker: "VGS", market: "asx" },
    { label: "NVTS", ticker: "NVTS", market: "us" },
    { label: "ETHA", ticker: "ETHA", market: "us" },
  ];

  const PANEL_WEIGHT = { price: 58, volume: 14, rsi: 14, macd: 14 };
  const PANEL_GAP = 0.028;

  const plotEl = document.getElementById("plotly-chart");
  const statusEl = document.getElementById("chart-status");
  const tickerInput = document.getElementById("chart-ticker-input");
  const tickerForm = document.getElementById("chart-ticker-form");
  const rangeToggle = document.getElementById("range-toggle");
  const watchList = document.getElementById("watch-sidebar-list");
  const indicatorToolbar = document.getElementById("indicator-toolbar");
  const metaEl = document.getElementById("ticker-meta-json");

  let currency = "USD";
  let market = app.dataset.market || "us";
  let symbol = app.dataset.symbol || "";
  let range = (app.dataset.range || "3M").toUpperCase();
  let loadToken = 0;
  let chartPayload = null;

  if (metaEl) {
    try {
      const m = JSON.parse(metaEl.textContent || "{}");
      if (m.currency) currency = m.currency;
      if (m.market) market = m.market;
    } catch {
      /* ignore */
    }
  }

  function formatMoney(n, cur) {
    if (n == null || Number.isNaN(n)) return "—";
    const c = cur || currency || "USD";
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: c,
        maximumFractionDigits: 2,
      }).format(n);
    } catch {
      return Number(n).toFixed(2) + " " + c;
    }
  }

  function formatChange(pct) {
    if (pct == null || Number.isNaN(pct)) return { text: "—", cls: "neutral" };
    const cls = pct > 0 ? "up" : pct < 0 ? "down" : "neutral";
    const arrow = pct > 0 ? "▲ +" : pct < 0 ? "▼ " : "";
    return { text: arrow + Math.abs(pct).toFixed(2) + "%", cls: cls };
  }

  function setStatus(msg, isError) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", Boolean(isError));
  }

  function setActiveRange(btnRange) {
    if (!rangeToggle) return;
    rangeToggle.querySelectorAll(".range-btn").forEach(function (btn) {
      btn.classList.toggle("is-active", btn.dataset.range === btnRange);
    });
  }

  function setActiveWatch(label) {
    if (!watchList) return;
    watchList.querySelectorAll(".watch-sidebar-item").forEach(function (btn) {
      btn.classList.toggle("is-active", btn.dataset.label === label);
    });
  }

  function getIndicatorFlags() {
    return {
      ma: Boolean(document.getElementById("ind-ma")?.checked),
      bb: Boolean(document.getElementById("ind-bb")?.checked),
      volume: Boolean(document.getElementById("ind-volume")?.checked),
      rsi: Boolean(document.getElementById("ind-rsi")?.checked),
      macd: Boolean(document.getElementById("ind-macd")?.checked),
    };
  }

  function buildPanelStack(flags) {
    const panels = ["price"];
    if (flags.volume) panels.push("volume");
    if (flags.rsi) panels.push("rsi");
    if (flags.macd) panels.push("macd");
    return panels;
  }

  function computeYDomains(panels) {
    const totalW = panels.reduce(function (sum, p) {
      return sum + PANEL_WEIGHT[p];
    }, 0);
    const available = 1 - PANEL_GAP * (panels.length - 1);
    let top = 1;
    const domains = {};
    panels.forEach(function (p) {
      const h = (PANEL_WEIGHT[p] / totalW) * available;
      domains[p] = [top - h, top];
      top = top - h - PANEL_GAP;
    });
    return domains;
  }

  function axisId(index, kind) {
    if (index === 0) return kind;
    return kind + (index + 1);
  }

  function updateQuoteHeader(payload) {
    const nameEl = document.getElementById("chart-name");
    const symEl = document.getElementById("chart-symbol");
    const exchEl = document.getElementById("chart-exchange");
    const lastEl = document.getElementById("display-last");
    const changeEl = document.getElementById("display-change");

    if (nameEl) nameEl.textContent = payload.name || payload.symbol || symbol;
    if (symEl) symEl.textContent = payload.symbol || symbol;
    if (exchEl && payload.exchange) exchEl.textContent = payload.exchange;
    if (payload.currency) currency = payload.currency;

    if (lastEl && payload.last != null) {
      lastEl.textContent = formatMoney(payload.last, payload.currency);
    }
    if (changeEl) {
      const ch = formatChange(payload.change_percent);
      changeEl.textContent = ch.text;
      changeEl.className = "chip q-change " + ch.cls;
    }
    if (tickerInput) tickerInput.value = payload.symbol || symbol;
    document.title = (payload.name || payload.symbol || symbol) + " — Financial Market Insights";
  }

  function syncUrl() {
    const path = "/ticker/" + encodeURIComponent(symbol);
    const url = new URL(path, window.location.origin);
    url.searchParams.set("market", market);
    url.searchParams.set("range", range);
    window.history.replaceState({ symbol: symbol, market: market, range: range }, "", url);
  }

  function spikeAxis() {
    return {
      showspikes: true,
      spikemode: "across",
      spikesnap: "cursor",
      spikethickness: 1,
      spikecolor: "rgba(148, 163, 184, 0.55)",
      spikedash: "dot",
    };
  }

  function renderChart(payload) {
    if (!payload || !plotEl) return;
    chartPayload = payload;

    const bars = payload.bars || [];
    if (!bars.length) return;

    const ind = payload.indicators || {};
    const flags = getIndicatorFlags();
    const panels = buildPanelStack(flags);
    const yDomains = computeYDomains(panels);
    const bottomPanel = panels[panels.length - 1];

    const x = bars.map(function (b) {
      return b.t;
    });

    const panelIndex = {};
    panels.forEach(function (p, i) {
      panelIndex[p] = i;
    });

    const traces = [];

    traces.push({
      type: "candlestick",
      name: payload.symbol,
      x: x,
      open: bars.map(function (b) {
        return b.o;
      }),
      high: bars.map(function (b) {
        return b.h;
      }),
      low: bars.map(function (b) {
        return b.l;
      }),
      close: bars.map(function (b) {
        return b.c;
      }),
      increasing: { line: { color: "#4ade80" }, fillcolor: "#4ade80" },
      decreasing: { line: { color: "#fb7185" }, fillcolor: "#fb7185" },
      xaxis: axisId(panelIndex.price, "x"),
      yaxis: axisId(panelIndex.price, "y"),
    });

    if (flags.ma) {
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "SMA 50",
        x: x,
        y: ind.sma50 || [],
        line: { color: "#38bdf8", width: 1.5 },
        xaxis: axisId(panelIndex.price, "x"),
        yaxis: axisId(panelIndex.price, "y"),
        hovertemplate: "SMA 50: %{y:.2f}<extra></extra>",
      });
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "SMA 200",
        x: x,
        y: ind.sma200 || [],
        line: { color: "#fbbf24", width: 1.5 },
        xaxis: axisId(panelIndex.price, "x"),
        yaxis: axisId(panelIndex.price, "y"),
        hovertemplate: "SMA 200: %{y:.2f}<extra></extra>",
      });
    }

    if (flags.bb) {
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "BB Upper",
        x: x,
        y: ind.bb_upper || [],
        line: { color: "rgba(129, 140, 248, 0.55)", width: 1 },
        xaxis: axisId(panelIndex.price, "x"),
        yaxis: axisId(panelIndex.price, "y"),
        hovertemplate: "BB Upper: %{y:.2f}<extra></extra>",
      });
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "BB Lower",
        x: x,
        y: ind.bb_lower || [],
        line: { color: "rgba(129, 140, 248, 0.55)", width: 1 },
        fill: "tonexty",
        fillcolor: "rgba(129, 140, 248, 0.1)",
        xaxis: axisId(panelIndex.price, "x"),
        yaxis: axisId(panelIndex.price, "y"),
        hovertemplate: "BB Lower: %{y:.2f}<extra></extra>",
      });
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "BB Mid",
        x: x,
        y: ind.bb_mid || [],
        line: { color: "rgba(148, 163, 184, 0.65)", width: 1, dash: "dot" },
        xaxis: axisId(panelIndex.price, "x"),
        yaxis: axisId(panelIndex.price, "y"),
        hovertemplate: "BB Mid: %{y:.2f}<extra></extra>",
      });
    }

    if (flags.volume && panelIndex.volume != null) {
      const volColors = bars.map(function (b) {
        return b.c >= b.o ? "rgba(74, 222, 128, 0.72)" : "rgba(251, 113, 133, 0.72)";
      });
      traces.push({
        type: "bar",
        name: "Volume",
        x: x,
        y: bars.map(function (b) {
          return b.v;
        }),
        marker: { color: volColors },
        xaxis: axisId(panelIndex.volume, "x"),
        yaxis: axisId(panelIndex.volume, "y"),
        hovertemplate: "Vol: %{y:,.0f}<extra></extra>",
      });
    }

    if (flags.rsi && panelIndex.rsi != null) {
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "RSI",
        x: x,
        y: ind.rsi || [],
        line: { color: "#a78bfa", width: 1.5 },
        xaxis: axisId(panelIndex.rsi, "x"),
        yaxis: axisId(panelIndex.rsi, "y"),
        hovertemplate: "RSI: %{y:.1f}<extra></extra>",
      });
    }

    if (flags.macd && panelIndex.macd != null) {
      const hist = ind.macd_hist || [];
      const histColors = hist.map(function (v) {
        if (v == null || Number.isNaN(v)) return "rgba(148, 163, 184, 0.4)";
        return v >= 0 ? "rgba(74, 222, 128, 0.75)" : "rgba(251, 113, 133, 0.75)";
      });
      traces.push({
        type: "bar",
        name: "MACD Hist",
        x: x,
        y: hist,
        marker: { color: histColors },
        xaxis: axisId(panelIndex.macd, "x"),
        yaxis: axisId(panelIndex.macd, "y"),
        hovertemplate: "Hist: %{y:.3f}<extra></extra>",
      });
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "MACD",
        x: x,
        y: ind.macd || [],
        line: { color: "#38bdf8", width: 1.4 },
        xaxis: axisId(panelIndex.macd, "x"),
        yaxis: axisId(panelIndex.macd, "y"),
        hovertemplate: "MACD: %{y:.3f}<extra></extra>",
      });
      traces.push({
        type: "scatter",
        mode: "lines",
        name: "Signal",
        x: x,
        y: ind.macd_signal || [],
        line: { color: "#f97316", width: 1.2 },
        xaxis: axisId(panelIndex.macd, "x"),
        yaxis: axisId(panelIndex.macd, "y"),
        hovertemplate: "Signal: %{y:.3f}<extra></extra>",
      });
    }

    const layout = {
      template: "plotly_dark",
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      margin: { l: 52, r: 16, t: 20, b: bottomPanel === "price" ? 36 : 28 },
      autosize: true,
      hovermode: "x unified",
      dragmode: "zoom",
      showlegend: flags.ma || flags.bb || flags.macd,
      legend: {
        orientation: "h",
        y: 1.02,
        x: 0,
        font: { size: 10, color: "#94a3b8" },
        bgcolor: "rgba(0,0,0,0)",
      },
      shapes: [],
    };

    panels.forEach(function (p, i) {
      const xKey = "xaxis" + (i === 0 ? "" : i + 1);
      const yKey = "yaxis" + (i === 0 ? "" : i + 1);
      const isBottom = p === bottomPanel;

      layout[xKey] = Object.assign(
        {
          domain: [0, 1],
          anchor: axisId(i, "y"),
          matches: i === 0 ? undefined : "x",
          showticklabels: isBottom,
          tickfont: { size: 11, color: "#64748b" },
          gridcolor: "rgba(148, 163, 184, 0.08)",
          type: payload.intraday ? "date" : "category",
        },
        i === 0 ? spikeAxis() : { showspikes: false }
      );

      const yCfg = {
        domain: yDomains[p],
        anchor: axisId(i, "x"),
        tickfont: { size: 11, color: "#64748b" },
        gridcolor: "rgba(148, 163, 184, 0.1)",
        zeroline: false,
      };

      if (p === "price") {
        Object.assign(yCfg, spikeAxis(), { tickformat: ",.2f" });
      } else if (p === "volume") {
        yCfg.tickformat = ",.0s";
      } else if (p === "rsi") {
        yCfg.range = [0, 100];
        yCfg.fixedrange = true;
        yCfg.tickvals = [30, 50, 70];
      } else if (p === "macd") {
        yCfg.tickformat = ",.2f";
        yCfg.zeroline = true;
        yCfg.zerolinecolor = "rgba(148, 163, 184, 0.25)";
      }

      layout[yKey] = yCfg;
    });

    if (flags.rsi && panelIndex.rsi != null) {
      const yref = axisId(panelIndex.rsi, "y");
      [30, 70].forEach(function (level) {
        layout.shapes.push({
          type: "line",
          xref: "paper",
          yref: yref,
          x0: 0,
          x1: 1,
          y0: level,
          y1: level,
          line: { color: "rgba(148, 163, 184, 0.35)", width: 1, dash: "dot" },
        });
      });
    }

    const config = {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      scrollZoom: true,
      modeBarButtonsToRemove: ["lasso2d", "select2d"],
    };

    Plotly.react(plotEl, traces, layout, config);

    const h = plotEl.clientHeight;
    if (h > 0) {
      Plotly.relayout(plotEl, { height: h });
    }

    plotEl.on("plotly_hover", function () {
      plotEl.style.cursor = "crosshair";
    });
    plotEl.on("plotly_unhover", function () {
      plotEl.style.cursor = "";
    });
  }

  function resizeChart() {
    if (!plotEl || !plotEl.querySelector(".plotly")) return;
    Plotly.Plots.resize(plotEl);
    const h = plotEl.clientHeight;
    if (h > 0) Plotly.relayout(plotEl, { height: h });
  }

  async function loadChart(nextTicker, nextMarket, nextRange, watchLabel) {
    const raw = (nextTicker || "").trim();
    if (!raw) {
      setStatus("Enter a ticker symbol.", true);
      return;
    }

    const reqMarket = nextMarket || market || "us";
    const reqRange = (nextRange || range || "3M").toUpperCase();
    const token = ++loadToken;

    symbol = raw.toUpperCase();
    market = reqMarket;
    range = reqRange;
    app.dataset.symbol = symbol;
    app.dataset.market = market;
    app.dataset.range = range;

    setActiveRange(range);
    if (watchLabel) setActiveWatch(watchLabel);
    setStatus("Loading…");
    syncUrl();

    try {
      const url = new URL("/api/ohlc", window.location.origin);
      url.searchParams.set("ticker", symbol);
      url.searchParams.set("market", market);
      url.searchParams.set("range", range);

      const res = await fetch(url.toString());
      const data = await res.json();
      if (token !== loadToken) return;

      if (!res.ok || !data.ok) {
        setStatus(data.error || "Could not load chart.", true);
        return;
      }

      symbol = data.symbol || symbol;
      updateQuoteHeader(data);
      renderChart(data);
      setStatus("");
      resizeChart();
    } catch (e) {
      if (token !== loadToken) return;
      setStatus(e.message || "Network error.", true);
    }
  }

  function buildWatchlist() {
    if (!watchList) return;
    watchList.innerHTML = "";

    DEFAULT_WATCHLIST.forEach(function (item) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "watch-sidebar-item";
      btn.dataset.label = item.label;
      btn.dataset.ticker = item.ticker;
      btn.dataset.market = item.market;
      btn.textContent = item.label;
      btn.addEventListener("click", function () {
        loadChart(item.ticker, item.market, range, item.label);
      });
      li.appendChild(btn);
      watchList.appendChild(li);
    });
  }

  if (rangeToggle) {
    rangeToggle.addEventListener("click", function (e) {
      const btn = e.target.closest(".range-btn");
      if (!btn || !btn.dataset.range) return;
      loadChart(symbol, market, btn.dataset.range);
    });
  }

  if (tickerForm) {
    tickerForm.addEventListener("submit", function (e) {
      e.preventDefault();
      loadChart(tickerInput ? tickerInput.value : symbol, "us", range);
    });
  }

  if (indicatorToolbar) {
    indicatorToolbar.addEventListener("change", function () {
      if (chartPayload) renderChart(chartPayload);
    });
  }

  buildWatchlist();
  setActiveRange(range);

  const initialLabel = DEFAULT_WATCHLIST.find(function (w) {
    return symbol.toUpperCase().startsWith(w.ticker) || symbol.toUpperCase() === w.ticker + ".AX";
  });
  if (initialLabel) setActiveWatch(initialLabel.label);

  loadChart(symbol, market, range, initialLabel ? initialLabel.label : null);

  window.addEventListener("resize", function () {
    resizeChart();
  });
})();
