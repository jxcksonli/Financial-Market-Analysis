(function () {
  const form = document.getElementById("lookup-form");
  const submitBtn = document.getElementById("submit-btn");
  if (!form || !submitBtn) return;

  const STORAGE_KEY = "fmi_watchlist_v1";
  const watchInput = document.getElementById("watch-ticker");
  const addBtn = document.getElementById("watch-add-btn");
  const clearBtn = document.getElementById("watch-clear-btn");
  const chipsEl = document.getElementById("watchlist-chips");
  const statusEl = document.getElementById("watch-status");
  const intervalEl = document.getElementById("watch-interval");
  const scaleEl = document.getElementById("watch-scale");
  const canvas = document.getElementById("watchlist-chart");
  const tbodyEl = document.getElementById("watchlist-tbody");

  let chart = null;

  function getSelectedMarket() {
    try {
      const m = new FormData(form).get("market");
      return (m || "us").toString();
    } catch {
      return "us";
    }
  }

  function normalizeTicker(raw, market) {
    const t = (raw || "").trim().toUpperCase();
    if (!t) return "";
    if (market === "asx") {
      return t.endsWith(".AX") ? t : t + ".AX";
    }
    return t.endsWith(".AX") ? t.slice(0, -3) : t;
  }

  async function isValidTicker(ticker, market) {
    const q = new URLSearchParams({
      ticker: ticker,
      market: market,
      interval: "day",
    });
    const res = await fetch("/api/quote?" + q.toString(), {
      headers: { Accept: "application/json" },
    });
    const data = await res.json().catch(() => null);
    if (!res.ok || !data || !data.ok) return null;
    return data.symbol || ticker;
  }

  async function resolveMarket(rawTicker) {
    const raw = (rawTicker || "").trim();
    if (!raw) return null;

    // Prefer explicit suffix if user typed it.
    const upper = raw.toUpperCase();
    const candidates = [];
    if (upper.endsWith(".AX")) {
      candidates.push({ market: "asx", ticker: normalizeTicker(upper, "asx") });
      candidates.push({ market: "us", ticker: normalizeTicker(upper, "us") });
    } else {
      candidates.push({ market: "us", ticker: normalizeTicker(upper, "us") });
      candidates.push({ market: "asx", ticker: normalizeTicker(upper, "asx") });
    }

    for (const c of candidates) {
      try {
        const sym = await isValidTicker(c.ticker, c.market);
        if (sym) return { market: c.market, ticker: sym };
      } catch {
        // ignore, try next
      }
    }
    return null;
  }

  function loadWatchlist() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const arr = JSON.parse(raw || "[]");
      if (!Array.isArray(arr)) return [];
      return arr
        .filter((x) => x && typeof x.ticker === "string" && typeof x.market === "string")
        .map((x) => ({ ticker: x.ticker, market: x.market }));
    } catch {
      return [];
    }
  }

  function saveWatchlist(items) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      /* ignore */
    }
  }

  function setStatus(msg, isError) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.classList.toggle("error", Boolean(isError));
  }

  function renderChips(items) {
    if (!chipsEl) return;
    chipsEl.innerHTML = "";
    items.forEach((it) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "watch-chip";
      chip.title = "Remove";
      chip.setAttribute("data-ticker", it.ticker);
      chip.setAttribute("data-market", it.market);
      chip.textContent = it.ticker + (it.market === "asx" ? " (ASX)" : " (US)");
      chipsEl.appendChild(chip);
    });
  }

  async function fetchSeries(item, interval) {
    const q = new URLSearchParams({
      ticker: item.ticker,
      market: item.market,
      interval: interval || "day",
    });
    const res = await fetch("/api/quote?" + q.toString(), { headers: { Accept: "application/json" } });
    const data = await res.json().catch(() => null);
    if (!res.ok || !data || !data.ok) {
      const err = (data && data.error) || ("Request failed (" + res.status + ")");
      throw new Error(item.ticker + ": " + err);
    }
    const series = (((data || {}).history || {}).series) || [];
    return Array.isArray(series) ? series : [];
  }

  async function fetchQuote(item, interval) {
    const q = new URLSearchParams({
      ticker: item.ticker,
      market: item.market,
      interval: interval || "day",
    });
    const res = await fetch("/api/quote?" + q.toString(), { headers: { Accept: "application/json" } });
    const data = await res.json().catch(() => null);
    if (!res.ok || !data || !data.ok) {
      const err = (data && data.error) || ("Request failed (" + res.status + ")");
      throw new Error(item.ticker + ": " + err);
    }
    return data;
  }

  function pctMoveFromSeries(series, lookbackDays) {
    if (!Array.isArray(series) || series.length <= lookbackDays) return null;
    const last = Number(series[series.length - 1].close);
    const prev = Number(series[series.length - (lookbackDays + 1)].close);
    if (!Number.isFinite(last) || !Number.isFinite(prev) || prev === 0) return null;
    return ((last / prev) - 1) * 100;
  }

  function trendFrom1m(pct1m) {
    if (pct1m == null || !Number.isFinite(pct1m)) return "—";
    if (pct1m > 2) return "Bullish";
    if (pct1m < -2) return "Bearish";
    return "Neutral";
  }

  function renderTable(rows) {
    if (!tbodyEl) return;
    tbodyEl.innerHTML = "";
    (rows || []).forEach((r) => {
      const tr = document.createElement("tr");

      const tdTicker = document.createElement("td");
      tdTicker.textContent = r.ticker + (r.market === "asx" ? " (ASX)" : "");
      tr.appendChild(tdTicker);

      function tdNum(val, suffix) {
        const td = document.createElement("td");
        td.className = "num " + (val == null ? "" : val > 0 ? "pos" : val < 0 ? "neg" : "");
        if (val == null || !Number.isFinite(val)) td.textContent = "—";
        else td.textContent = val.toFixed(2) + (suffix || "");
        return td;
      }

      tr.appendChild(tdNum(r.last, ""));
      tr.appendChild(tdNum(r.d1, "%"));
      tr.appendChild(tdNum(r.w1, "%"));
      tr.appendChild(tdNum(r.m1, "%"));

      const tdTrend = document.createElement("td");
      tdTrend.className = "trend";
      tdTrend.textContent = r.trend || "—";
      tr.appendChild(tdTrend);

      tbodyEl.appendChild(tr);
    });
  }

  function buildAligned(labels, dateToValue) {
    return labels.map((d) => (Object.prototype.hasOwnProperty.call(dateToValue, d) ? dateToValue[d] : null));
  }

  function toPctChange(series) {
    // Convert [number|null] into percent change from first non-null point.
    let base = null;
    for (let i = 0; i < series.length; i++) {
      const v = series[i];
      if (v != null && Number.isFinite(v)) {
        base = v;
        break;
      }
    }
    if (base == null || base === 0) return series.map(() => null);
    return series.map((v) => {
      if (v == null || !Number.isFinite(v)) return null;
      return ((v / base) - 1) * 100;
    });
  }

  function palette(i) {
    const colors = [
      "rgb(56, 189, 248)",
      "rgb(129, 140, 248)",
      "rgb(74, 222, 128)",
      "rgb(251, 113, 133)",
      "rgb(250, 204, 21)",
      "rgb(45, 212, 191)",
      "rgb(244, 114, 182)",
    ];
    return colors[i % colors.length];
  }

  async function redraw() {
    if (!canvas || typeof Chart === "undefined" || !intervalEl) return;
    const items = loadWatchlist();
    renderChips(items);

    if (!items.length) {
      setStatus("Add tickers to start tracking.", false);
      if (chart) {
        chart.destroy();
        chart = null;
      }
      return;
    }

    setStatus("Loading…", false);
    const interval = intervalEl.value || "day";
    const scaleMode = (scaleEl && scaleEl.value) || "pct";

    let results;
    try {
      results = await Promise.all(
        items.map(async (it) => ({ it, series: await fetchSeries(it, interval) }))
      );
    } catch (e) {
      setStatus((e && e.message) || "Failed to load watchlist.", true);
      return;
    }

    // union of dates
    const dateSet = new Set();
    results.forEach((r) => {
      (r.series || []).forEach((p) => {
        if (p && typeof p.date === "string") dateSet.add(p.date);
      });
    });
    const labels = Array.from(dateSet).sort();

    const datasets = results.map((r, idx) => {
      const m = {};
      (r.series || []).forEach((p) => {
        if (!p || typeof p.date !== "string") return;
        const v = Number(p.close);
        if (!Number.isFinite(v)) return;
        m[p.date] = v;
      });
      const c = palette(idx);
      const aligned = buildAligned(labels, m);
      const data = scaleMode === "pct" ? toPctChange(aligned) : aligned;
      return {
        label: r.it.ticker,
        data: data,
        borderColor: c,
        backgroundColor: c,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 3,
        borderWidth: 2.25,
        spanGaps: true,
      };
    });

    if (chart) chart.destroy();
    chart = new Chart(canvas, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { display: true, labels: { color: "#94a3b8", boxWidth: 10 } },
          tooltip: {
            backgroundColor: "rgba(15, 23, 42, 0.92)",
            titleColor: "#e2e8f0",
            bodyColor: "#f1f5f9",
            borderColor: "rgba(148, 163, 184, 0.25)",
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10,
            displayColors: true,
            callbacks: {
              label: function (ctx) {
                const y = ctx.parsed && typeof ctx.parsed.y === "number" ? ctx.parsed.y : null;
                if (y == null || Number.isNaN(y)) return ctx.dataset.label + ": —";
                if (scaleMode === "pct") return ctx.dataset.label + ": " + y.toFixed(2) + "%";
                return ctx.dataset.label + ": " + y.toFixed(2);
              },
            },
          },
        },
        scales: {
          x: {
            ticks: { maxTicksLimit: 10, color: "#64748b", font: { size: 11 } },
            grid: { color: "rgba(148, 163, 184, 0.08)" },
            border: { display: false },
          },
          y: {
            ticks: {
              color: "#64748b",
              font: { size: 11 },
              callback: function (value) {
                if (scaleMode === "pct") return Number(value).toFixed(1) + "%";
                return value;
              },
            },
            grid: { color: "rgba(148, 163, 184, 0.1)" },
            border: { display: false },
          },
        },
      },
    });

    // Summary table always uses daily history so 1D/1W/1M are consistent.
    if (tbodyEl) {
      try {
        const quotes = await Promise.all(items.map(async (it) => ({ it, q: await fetchQuote(it, "day") })));
        const rows = quotes.map(({ it, q }) => {
          const series = (((q || {}).history || {}).series) || [];
          const last = Number(q.last);
          const d1 = Number.isFinite(q.change_percent) ? Number(q.change_percent) : pctMoveFromSeries(series, 1);
          const w1 = pctMoveFromSeries(series, 5);
          const m1 = pctMoveFromSeries(series, 21);
          return {
            ticker: it.ticker,
            market: it.market,
            last: Number.isFinite(last) ? last : null,
            d1: d1 != null && Number.isFinite(d1) ? d1 : null,
            w1: w1,
            m1: m1,
            trend: trendFrom1m(m1),
          };
        });
        renderTable(rows);
      } catch (e) {
        renderTable([]);
        setStatus((e && e.message) || "Loaded chart but failed to load table.", true);
        return;
      }
    }

    setStatus("Loaded " + items.length + " tickers.", false);
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const ticker = (document.getElementById("ticker") || {}).value;
    if (!ticker || !ticker.trim()) return;
    const market =
      (new FormData(form).get("market") || "us").toString();
    const path = "/ticker/" + encodeURIComponent(ticker.trim());
    const q = new URLSearchParams({ market });
    window.location.href = path + "?" + q.toString();
  });

  if (addBtn && watchInput) {
    addBtn.addEventListener("click", async function () {
      if (addBtn.disabled) return;
      const raw = (watchInput.value || "").trim();
      if (!raw) return;

      addBtn.disabled = true;
      setStatus("Validating ticker…", false);

      const resolved = await resolveMarket(raw);
      if (!resolved) {
        setStatus(
          'Could not add "' +
            raw +
            '" — not found on US or ASX. Check the symbol and try again.',
          true
        );
        addBtn.disabled = false;
        return;
      }

      const items = loadWatchlist();
      const key = resolved.ticker + "|" + resolved.market;
      const seen = new Set(items.map((x) => x.ticker + "|" + x.market));
      if (!seen.has(key)) {
        items.push({ ticker: resolved.ticker, market: resolved.market });
        saveWatchlist(items);
      }

      watchInput.value = "";
      addBtn.disabled = false;
      redraw();
    });

    watchInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        addBtn.click();
      }
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      saveWatchlist([]);
      redraw();
    });
  }

  if (chipsEl) {
    chipsEl.addEventListener("click", function (e) {
      const btn = e.target && e.target.closest ? e.target.closest("button.watch-chip") : null;
      if (!btn) return;
      const t = btn.getAttribute("data-ticker");
      const m = btn.getAttribute("data-market");
      const items = loadWatchlist().filter((x) => !(x.ticker === t && x.market === m));
      saveWatchlist(items);
      redraw();
    });
  }

  if (intervalEl) {
    intervalEl.addEventListener("change", function () {
      redraw();
    });
  }

  if (scaleEl) {
    scaleEl.addEventListener("change", function () {
      redraw();
    });
  }

  // Initial render
  redraw();
})();
