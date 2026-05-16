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
  const sentimentRefreshBtn = document.getElementById("sentiment-refresh-btn");
  const watchSentimentStatus = document.getElementById("watch-sentiment-status");
  const indicatorToolbar = document.getElementById("indicator-toolbar");
  const metaEl = document.getElementById("ticker-meta-json");
  const newsSidebar = document.getElementById("news-sidebar");
  const newsCollapseBtn = document.getElementById("news-collapse-btn");
  const newsList = document.getElementById("news-list");
  const newsStatus = document.getElementById("news-status");
  const newsFilter = document.getElementById("news-filter");
  const newsSymbolLabel = document.getElementById("news-symbol-label");
  const newsWatchTabs = document.getElementById("news-watch-tabs");
  const tabNews = document.getElementById("tab-news");
  const tabEvents = document.getElementById("tab-events");
  const paneNews = document.getElementById("side-panel-news");
  const paneEvents = document.getElementById("side-panel-events");
  const earningsEventsList = document.getElementById("earnings-events-list");
  const macroEventsList = document.getElementById("macro-events-list");
  const eventsStatus = document.getElementById("events-status");

  const NEWS_REFRESH_MS = 5 * 60 * 1000;
  const NEWS_COLLAPSE_KEY = "news-panel-collapsed";

  let currency = "USD";
  let market = app.dataset.market || "us";
  let symbol = app.dataset.symbol || "";
  let range = (app.dataset.range || "3M").toUpperCase();
  let loadToken = 0;
  let chartPayload = null;
  let newsToken = 0;
  let newsTicker = symbol;
  let newsMarket = market;
  let newsRefreshTimer = null;
  let eventsToken = 0;
  let chartEventMarkers = [];

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
    setActiveNewsTab(label);
  }

  function setActiveNewsTab(label) {
    if (!newsWatchTabs) return;
    newsWatchTabs.querySelectorAll(".news-watch-tab").forEach(function (btn) {
      const match =
        label &&
        (btn.dataset.label === label ||
          btn.dataset.ticker === label ||
          btn.dataset.ticker === (label || "").replace(".AX", ""));
      btn.classList.toggle("is-active", Boolean(match));
    });
  }

  function syncNewsTabForSymbol(sym) {
    const upper = (sym || "").toUpperCase();
    const hit = DEFAULT_WATCHLIST.find(function (w) {
      return upper === w.ticker || upper === w.ticker + ".AX" || upper.startsWith(w.ticker);
    });
    setActiveNewsTab(hit ? hit.label : null);
  }

  function setNewsStatus(msg, isError) {
    if (!newsStatus) return;
    newsStatus.textContent = msg || "";
    newsStatus.classList.toggle("error", Boolean(isError));
  }

  function renderNewsList(items) {
    if (!newsList) return;
    newsList.innerHTML = "";
    if (!items || !items.length) {
      const li = document.createElement("li");
      li.className = "news-item news-item--empty";
      li.textContent = "No headlines found for this filter.";
      newsList.appendChild(li);
      return;
    }
    items.forEach(function (item) {
      const li = document.createElement("li");
      li.className = "news-item";
      const a = document.createElement("a");
      a.className = "news-link";
      a.href = item.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";

      const h = document.createElement("p");
      h.className = "news-headline";
      h.textContent = item.headline;

      const meta = document.createElement("p");
      meta.className = "news-meta";
      if (item.source) {
        const src = document.createElement("span");
        src.className = "news-meta-source";
        src.textContent = item.source;
        meta.appendChild(src);
      }
      if (item.time_ago) {
        const t = document.createElement("span");
        t.textContent = item.time_ago;
        meta.appendChild(t);
      }
      if (item.category) {
        const tag = document.createElement("span");
        tag.className = "news-meta-tag";
        tag.textContent = item.category === "company" ? "Company" : "Market";
        meta.appendChild(tag);
      }

      a.appendChild(h);
      a.appendChild(meta);
      li.appendChild(a);
      newsList.appendChild(li);
    });
  }

  async function loadNews(nextTicker, nextMarket) {
    const raw = (nextTicker || newsTicker || symbol || "").trim();
    if (!raw) return;

    const reqMarket = nextMarket || newsMarket || market || "us";
    const filt = (newsFilter && newsFilter.value) || "all";
    const token = ++newsToken;

    newsTicker = raw.toUpperCase();
    newsMarket = reqMarket;
    if (newsSymbolLabel) newsSymbolLabel.textContent = newsTicker;

    setNewsStatus("Loading news…");

    try {
      const url = new URL("/api/news", window.location.origin);
      url.searchParams.set("ticker", newsTicker);
      url.searchParams.set("market", newsMarket);
      url.searchParams.set("filter", filt);

      const res = await fetch(url.toString());
      const data = await res.json();
      if (token !== newsToken) return;

      if (!res.ok || !data.ok) {
        setNewsStatus(data.error || "Could not load news.", true);
        renderNewsList([]);
        return;
      }

      newsTicker = data.symbol || newsTicker;
      if (newsSymbolLabel) {
        const fh = data.finnhub_symbol && data.finnhub_symbol !== newsTicker;
        newsSymbolLabel.textContent = fh
          ? newsTicker + " · " + data.finnhub_symbol
          : newsTicker;
      }
      renderNewsList(data.items || []);
      const n = (data.items || []).length;
      setNewsStatus(n ? "Updated " + new Date().toLocaleTimeString() : "");
    } catch (e) {
      if (token !== newsToken) return;
      setNewsStatus(e.message || "Network error.", true);
      renderNewsList([]);
    }
  }

  function startNewsRefresh() {
    if (newsRefreshTimer) clearInterval(newsRefreshTimer);
    newsRefreshTimer = setInterval(function () {
      loadNews(newsTicker, newsMarket);
    }, NEWS_REFRESH_MS);
  }

  function buildNewsWatchTabs() {
    if (!newsWatchTabs) return;
    newsWatchTabs.innerHTML = "";
    DEFAULT_WATCHLIST.forEach(function (item) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "news-watch-tab";
      btn.dataset.label = item.label;
      btn.dataset.ticker = item.ticker;
      btn.dataset.market = item.market;
      btn.setAttribute("role", "tab");
      btn.textContent = item.label;
      btn.addEventListener("click", function () {
        setActiveNewsTab(item.label);
        loadNews(item.ticker, item.market);
      });
      newsWatchTabs.appendChild(btn);
    });
  }

  function initNewsCollapse() {
    if (!newsSidebar || !newsCollapseBtn) return;
    const collapsed = localStorage.getItem(NEWS_COLLAPSE_KEY) === "1";
    newsSidebar.classList.toggle("is-collapsed", collapsed);
    newsCollapseBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    newsCollapseBtn.title = collapsed ? "Expand news panel" : "Collapse news panel";

    newsCollapseBtn.addEventListener("click", function () {
      const nowCollapsed = !newsSidebar.classList.contains("is-collapsed");
      newsSidebar.classList.toggle("is-collapsed", nowCollapsed);
      newsCollapseBtn.setAttribute("aria-expanded", nowCollapsed ? "false" : "true");
      newsCollapseBtn.title = nowCollapsed ? "Expand news panel" : "Collapse news panel";
      localStorage.setItem(NEWS_COLLAPSE_KEY, nowCollapsed ? "1" : "0");
      resizeChart();
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

  function buildEventMarkerShapes(markers, priceXAxis) {
    const xref = priceXAxis || "x";
    const shapes = [];
    (markers || []).forEach(function (m) {
      if (!m || !m.x) return;
      const isEarnings = m.type === "earnings";
      shapes.push({
        type: "line",
        xref: xref,
        yref: "y domain",
        x0: m.x,
        x1: m.x,
        y0: 0,
        y1: 1,
        line: {
          color: isEarnings ? "rgba(251, 191, 36, 0.75)" : "rgba(129, 140, 248, 0.65)",
          width: 1,
          dash: "dash",
        },
      });
    });
    return shapes;
  }

  function formatDaysUntil(days) {
    if (days == null || Number.isNaN(days)) return "";
    if (days === 0) return "Today";
    if (days === 1) return "1 day";
    if (days > 0) return days + " days";
    if (days === -1) return "1 day ago";
    return Math.abs(days) + " days ago";
  }

  function setEventsStatus(msg, isError) {
    if (!eventsStatus) return;
    eventsStatus.textContent = msg || "";
    eventsStatus.classList.toggle("error", Boolean(isError));
  }

  function renderEarningsEvents(items) {
    if (!earningsEventsList) return;
    earningsEventsList.innerHTML = "";
    if (!items || !items.length) {
      const li = document.createElement("li");
      li.className = "event-row";
      li.textContent = "No upcoming earnings in the next 90 days.";
      earningsEventsList.appendChild(li);
      return;
    }
    items.forEach(function (ev) {
      const li = document.createElement("li");
      li.className = "event-row" + (ev.soon ? " is-soon" : "");

      const head = document.createElement("div");
      head.className = "event-row-head";
      const sym = document.createElement("span");
      sym.className = "event-row-symbol";
      sym.textContent = ev.symbol;
      const dt = document.createElement("span");
      dt.className = "event-row-date";
      dt.textContent = ev.date;
      head.appendChild(sym);
      head.appendChild(dt);

      const meta = document.createElement("p");
      meta.className = "event-row-meta";
      const parts = [];
      if (ev.eps_estimate != null) parts.push("Est. EPS " + ev.eps_estimate);
      if (ev.eps_previous != null) parts.push("Prev. EPS " + ev.eps_previous);
      meta.textContent = parts.join(" · ") || "EPS TBA";
      const days = document.createElement("span");
      days.className = "event-row-days";
      days.textContent = " · " + formatDaysUntil(ev.days_until);
      meta.appendChild(days);

      li.appendChild(head);
      li.appendChild(meta);
      earningsEventsList.appendChild(li);
    });
  }

  function renderMacroEvents(items) {
    if (!macroEventsList) return;
    macroEventsList.innerHTML = "";
    if (!items || !items.length) {
      const li = document.createElement("li");
      li.className = "event-cal-row";
      li.textContent = "No upcoming macro events scheduled.";
      macroEventsList.appendChild(li);
      return;
    }
    items.forEach(function (ev) {
      const li = document.createElement("li");
      li.className = "event-cal-row" + (ev.soon ? " is-soon" : "");

      const d = document.createElement("span");
      d.className = "event-cal-date";
      d.textContent = ev.date;

      const title = document.createElement("span");
      title.className = "event-cal-title";
      title.textContent = ev.title;

      const days = document.createElement("span");
      days.className = "event-cal-days";
      days.textContent = formatDaysUntil(ev.days_until);

      li.appendChild(d);
      li.appendChild(title);
      li.appendChild(days);
      macroEventsList.appendChild(li);
    });
  }

  async function loadEvents() {
    const token = ++eventsToken;
    setEventsStatus("Loading events…");

    try {
      const url = new URL("/api/events", window.location.origin);
      url.searchParams.set("ticker", symbol);
      url.searchParams.set("market", market);
      url.searchParams.set("range", range);

      const res = await fetch(url.toString());
      const data = await res.json();
      if (token !== eventsToken) return;

      if (!res.ok || !data.ok) {
        setEventsStatus(data.error || "Could not load events.", true);
        chartEventMarkers = [];
        if (chartPayload) renderChart(chartPayload);
        return;
      }

      renderEarningsEvents(data.earnings || []);
      renderMacroEvents(data.macro || []);
      chartEventMarkers = data.chart_markers || [];
      setEventsStatus("");
      if (chartPayload) renderChart(chartPayload);
    } catch (e) {
      if (token !== eventsToken) return;
      setEventsStatus(e.message || "Network error.", true);
      chartEventMarkers = [];
      if (chartPayload) renderChart(chartPayload);
    }
  }

  function initSidePanelTabs() {
    function activate(panel) {
      const isNews = panel === "news";
      if (tabNews) {
        tabNews.classList.toggle("is-active", isNews);
        tabNews.setAttribute("aria-selected", isNews ? "true" : "false");
      }
      if (tabEvents) {
        tabEvents.classList.toggle("is-active", !isNews);
        tabEvents.setAttribute("aria-selected", !isNews ? "true" : "false");
      }
      if (paneNews) {
        paneNews.classList.toggle("is-active", isNews);
        paneNews.hidden = !isNews;
      }
      if (paneEvents) {
        paneEvents.classList.toggle("is-active", !isNews);
        paneEvents.hidden = isNews;
      }
    }
    if (tabNews) {
      tabNews.addEventListener("click", function () {
        activate("news");
      });
    }
    if (tabEvents) {
      tabEvents.addEventListener("click", function () {
        activate("events");
      });
    }
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

    const priceXRef = axisId(panelIndex.price, "x");
    buildEventMarkerShapes(chartEventMarkers, priceXRef).forEach(function (shape) {
      layout.shapes.push(shape);
    });

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
      loadNews(symbol, market);
      syncNewsTabForSymbol(symbol);
      loadEvents();
    } catch (e) {
      if (token !== loadToken) return;
      setStatus(e.message || "Network error.", true);
    }
  }

  function sentimentBadgeClass(sentiment) {
    if (sentiment === "bullish") return "sentiment-badge sentiment-bullish";
    if (sentiment === "bearish") return "sentiment-badge sentiment-bearish";
    return "sentiment-badge sentiment-neutral";
  }

  function setWatchSentimentStatus(msg, isError) {
    if (!watchSentimentStatus) return;
    watchSentimentStatus.textContent = msg || "";
    watchSentimentStatus.classList.toggle("error", Boolean(isError));
  }

  function applySentimentToWatchlist(items) {
    if (!watchList || !items) return;
    const byLabel = {};
    items.forEach(function (row) {
      byLabel[row.label] = row;
    });

    watchList.querySelectorAll(".watch-sidebar-item").forEach(function (btn) {
      const label = btn.dataset.label;
      const row = byLabel[label];
      const badge = btn.querySelector(".sentiment-badge");
      if (!badge || !row) return;

      badge.className = sentimentBadgeClass(row.sentiment);
      badge.classList.remove("sentiment-loading");
      const tip = row.reason + " — Risk: " + row.key_risk;
      badge.setAttribute("data-tip", tip);
    });
  }

  async function loadSentiment(forceRefresh) {
    if (sentimentRefreshBtn) sentimentRefreshBtn.disabled = true;
    setWatchSentimentStatus(forceRefresh ? "Refreshing sentiment…" : "Loading sentiment…");

    try {
      const url = new URL("/api/sentiment", window.location.origin);
      if (forceRefresh) url.searchParams.set("refresh", "1");

      const res = await fetch(url.toString());
      const data = await res.json();

      if (!res.ok || !data.ok) {
        setWatchSentimentStatus(data.error || "Could not load sentiment.", true);
        return;
      }

      applySentimentToWatchlist(data.items || []);
      const cached = (data.items || []).every(function (r) {
        return r.from_cache;
      });
      const mins = Math.round((data.cache_ttl_sec || 1800) / 60);
      if (forceRefresh) {
        setWatchSentimentStatus("Sentiment updated just now.");
      } else if (cached) {
        setWatchSentimentStatus("Cached · refreshes in ~" + mins + " min");
      } else {
        setWatchSentimentStatus("Sentiment updated.");
      }
    } catch (e) {
      setWatchSentimentStatus(e.message || "Network error.", true);
    } finally {
      if (sentimentRefreshBtn) sentimentRefreshBtn.disabled = false;
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

      const labelSpan = document.createElement("span");
      labelSpan.className = "watch-item-label";
      labelSpan.textContent = item.label;

      const badge = document.createElement("span");
      badge.className = "sentiment-badge sentiment-neutral sentiment-loading";
      badge.setAttribute("aria-label", "Sentiment loading");
      badge.setAttribute("data-tip", "Sentiment loading…");

      btn.appendChild(labelSpan);
      btn.appendChild(badge);
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

  if (newsFilter) {
    newsFilter.addEventListener("change", function () {
      loadNews(newsTicker, newsMarket);
    });
  }

  buildNewsWatchTabs();
  initNewsCollapse();
  initSidePanelTabs();
  buildWatchlist();
  setActiveRange(range);
  startNewsRefresh();

  if (sentimentRefreshBtn) {
    sentimentRefreshBtn.addEventListener("click", function () {
      loadSentiment(true);
    });
  }
  loadSentiment(false);

  const initialLabel = DEFAULT_WATCHLIST.find(function (w) {
    return symbol.toUpperCase().startsWith(w.ticker) || symbol.toUpperCase() === w.ticker + ".AX";
  });
  if (initialLabel) setActiveWatch(initialLabel.label);

  loadChart(symbol, market, range, initialLabel ? initialLabel.label : null);

  window.addEventListener("resize", function () {
    resizeChart();
  });
})();
