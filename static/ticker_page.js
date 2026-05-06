(function () {
  const el = document.getElementById("ticker-chart-data");
  const metaEl = document.getElementById("ticker-meta-json");
  if (!el || typeof Chart === "undefined") return;

  const intervalSelect = document.getElementById("interval");
  if (intervalSelect) {
    intervalSelect.addEventListener("change", function () {
      const url = new URL(window.location.href);
      url.searchParams.set("interval", intervalSelect.value || "day");
      window.location.href = url.toString();
    });
  }

  let series;
  try {
    series = JSON.parse(el.textContent || "[]");
  } catch {
    return;
  }
  if (!Array.isArray(series) || !series.length) return;

  let markers = [];
  const markersEl = document.getElementById("ticker-markers-json");
  if (markersEl) {
    try {
      const m = JSON.parse(markersEl.textContent || "[]");
      if (Array.isArray(m)) markers = m;
    } catch {
      /* ignore */
    }
  }

  let currency = "USD";
  if (metaEl) {
    try {
      const m = JSON.parse(metaEl.textContent || "{}");
      if (m.currency) currency = m.currency;
    } catch {
      /* ignore */
    }
  }

  const canvas = document.getElementById("template-chart");
  if (!canvas) return;

  const labels = series.map(function (p) {
    return p.date;
  });
  const values = series.map(function (p) {
    return p.close;
  });

  const line = "rgb(56, 189, 248)";
  const fillTop = "rgba(56, 189, 248, 0.24)";
  const fillBot = "rgba(129, 140, 248, 0.02)";

  function formatMoney(n) {
    if (n == null || Number.isNaN(n)) return "—";
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: currency,
        maximumFractionDigits: 2,
      }).format(n);
    } catch {
      return n.toFixed(2) + " " + currency;
    }
  }

  function shortLabel(s, maxLen) {
    const str = (s || "").toString().trim();
    if (!str) return "";
    if (str.length <= maxLen) return str;
    return str.slice(0, maxLen - 1).trimEnd() + "…";
  }

  const markerPlugin = {
    id: "markerPlugin",
    afterDatasetsDraw(chart) {
      if (!markers || !markers.length) return;
      const ctx = chart.ctx;
      const xScale = chart.scales.x;
      const yScale = chart.scales.y;
      if (!xScale || !yScale) return;

      ctx.save();
      ctx.font = "600 11px Outfit, system-ui, sans-serif";
      ctx.textBaseline = "bottom";

      markers.forEach((m) => {
        if (!m || typeof m.date !== "string") return;
        const idx = labels.indexOf(m.date);
        if (idx < 0) return;
        const x = xScale.getPixelForValue(idx);
        const yVal = values[idx];
        if (yVal == null || Number.isNaN(yVal)) return;
        const y = yScale.getPixelForValue(yVal);

        const isDip = m.kind === "dip";
        const color = isDip ? "rgba(251, 113, 133, 0.95)" : "rgba(74, 222, 128, 0.95)";

        // Vertical tick
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x, y - 6);
        ctx.lineTo(x, y + 6);
        ctx.stroke();

        // Label box
        const label = shortLabel(m.label || "", 58);
        if (!label) return;
        const padX = 8;
        const padY = 6;
        const textW = ctx.measureText(label).width;
        const boxW = textW + padX * 2;
        const boxH = 22;
        const boxX = Math.min(Math.max(x + 8, chart.chartArea.left + 6), chart.chartArea.right - boxW - 6);
        const boxY = Math.max(chart.chartArea.top + boxH + 6, y - 10);

        ctx.fillStyle = "rgba(15, 23, 42, 0.92)";
        ctx.strokeStyle = "rgba(148, 163, 184, 0.22)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(boxX, boxY - boxH, boxW, boxH, 10);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = color;
        ctx.fillText(label, boxX + padX, boxY - padY);
      });

      ctx.restore();
    },
  };

  const markerPoints = (markers || [])
    .map(function (m) {
      if (!m || typeof m.date !== "string") return null;
      const idx = labels.indexOf(m.date);
      if (idx < 0) return null;
      const y = values[idx];
      if (y == null || Number.isNaN(y)) return null;
      return {
        x: idx,
        y: y,
        kind: m.kind || "",
        label: m.label || "",
        url: m.url || "",
      };
    })
    .filter(Boolean);

  const markerDataset = {
    type: "scatter",
    label: "Events",
    data: markerPoints,
    showLine: false,
    parsing: false,
    pointRadius: 4,
    pointHoverRadius: 7,
    pointHitRadius: 14,
    pointBorderWidth: 2,
    pointBorderColor: "rgba(15, 23, 42, 0.92)",
    pointBackgroundColor: function (ctx) {
      const p = ctx.raw || {};
      const isDip = p.kind === "dip";
      return isDip ? "rgba(251, 113, 133, 0.95)" : "rgba(74, 222, 128, 0.95)";
    },
  };

  function ensureModal() {
    let el = document.getElementById("event-modal");
    if (el) return el;
    el = document.createElement("div");
    el.id = "event-modal";
    el.style.position = "fixed";
    el.style.inset = "0";
    el.style.background = "rgba(0,0,0,0.55)";
    el.style.display = "none";
    el.style.alignItems = "center";
    el.style.justifyContent = "center";
    el.style.padding = "1.25rem";
    el.style.zIndex = "50";

    el.innerHTML =
      '<div id="event-modal-card" style="' +
      "max-width:720px;width:100%;" +
      "background:rgba(14,18,28,0.92);" +
      "border:1px solid rgba(255,255,255,0.12);" +
      "border-radius:16px;" +
      "box-shadow:0 16px 60px rgba(0,0,0,0.6);" +
      "padding:1rem 1rem 0.9rem;" +
      '">' +
      '<div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">' +
      '<div style="min-width:0;">' +
      '<div id="event-modal-date" style="font:600 0.72rem Outfit,system-ui,sans-serif;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;margin-bottom:0.45rem;"></div>' +
      '<div id="event-modal-title" style="font:700 1.05rem Outfit,system-ui,sans-serif;color:#f1f5f9;line-height:1.35;word-break:break-word;"></div>' +
      "</div>" +
      '<button id="event-modal-close" type="button" style="' +
      "border:1px solid rgba(255,255,255,0.14);" +
      "background:rgba(255,255,255,0.06);" +
      "color:#f1f5f9;" +
      "border-radius:10px;" +
      "padding:0.4rem 0.6rem;" +
      "cursor:pointer;" +
      '">Close</button>' +
      "</div>" +
      '<div style="margin-top:0.75rem;display:flex;gap:0.6rem;flex-wrap:wrap;">' +
      '<a id="event-modal-link" href="#" target="_blank" rel="noopener noreferrer" style="' +
      "text-decoration:none;" +
      "display:inline-flex;align-items:center;justify-content:center;" +
      "padding:0.55rem 0.85rem;" +
      "border-radius:12px;" +
      "border:1px solid rgba(56,189,248,0.35);" +
      "background:rgba(56,189,248,0.12);" +
      "color:#38bdf8;" +
      "font:600 0.92rem Outfit,system-ui,sans-serif;" +
      '">Read more</a>' +
      "</div>" +
      "</div>";

    document.body.appendChild(el);

    el.addEventListener("click", function (e) {
      const card = document.getElementById("event-modal-card");
      if (card && !card.contains(e.target)) hideModal();
    });
    const closeBtn = el.querySelector("#event-modal-close");
    if (closeBtn) closeBtn.addEventListener("click", hideModal);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") hideModal();
    });
    return el;
  }

  function showModal(payload) {
    const el = ensureModal();
    const dateEl = el.querySelector("#event-modal-date");
    const titleEl = el.querySelector("#event-modal-title");
    const linkEl = el.querySelector("#event-modal-link");
    if (dateEl) dateEl.textContent = payload.date || "";
    if (titleEl) titleEl.textContent = payload.label || "Event";
    if (linkEl) {
      if (payload.url) {
        linkEl.style.display = "inline-flex";
        linkEl.setAttribute("href", payload.url);
      } else {
        linkEl.style.display = "none";
        linkEl.setAttribute("href", "#");
      }
    }
    el.style.display = "flex";
  }

  function hideModal() {
    const el = document.getElementById("event-modal");
    if (el) el.style.display = "none";
  }

  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Close (template)",
          data: values,
          borderColor: line,
          backgroundColor: function (context) {
            const chart = context.chart;
            const chartArea = chart.chartArea;
            if (!chartArea) return fillTop;
            const g = chart.ctx.createLinearGradient(
              0,
              chartArea.top,
              0,
              chartArea.bottom
            );
            g.addColorStop(0, fillTop);
            g.addColorStop(1, fillBot);
            return g;
          },
          fill: true,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 4,
          borderWidth: 2.5,
        },
        markerDataset,
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      onClick: function (evt) {
        // Make clicks work even when user clicks the vertical marker tick, not the dot.
        const rect = canvas.getBoundingClientRect();
        const mx = evt.x - rect.left;
        const my = evt.y - rect.top;

        // First, ask Chart.js which element is closest (intersect=false is forgiving).
        const nearest = chart.getElementsAtEventForMode(
          evt,
          "nearest",
          { intersect: false },
          true
        );
        if (nearest && nearest.length) {
          const el0 = nearest[0];
          const ds0 = chart.data.datasets[el0.datasetIndex];
          if (ds0 && ds0.label === "Events") {
            const p0 = ds0.data[el0.index];
            showModal({
              date: labels[p0.x] || "",
              label: p0.label || "Event",
              url: p0.url || "",
            });
            return;
          }
        }

        // Fallback: manual hit-test against marker pixels (covers custom drawn ticks/labels).
        const xScale = chart.scales.x;
        const yScale = chart.scales.y;
        if (!xScale || !yScale) return;

        let best = null;
        let bestDist = Infinity;
        (markerPoints || []).forEach(function (p) {
          const px = xScale.getPixelForValue(p.x);
          const py = yScale.getPixelForValue(p.y);
          const dx = mx - px;
          const dy = my - py;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < bestDist) {
            bestDist = dist;
            best = p;
          }
        });
        if (best && bestDist <= 16) {
          showModal({
            date: labels[best.x] || "",
            label: best.label || "Event",
            url: best.url || "",
          });
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.92)",
          titleColor: "#e2e8f0",
          bodyColor: "#f1f5f9",
          borderColor: "rgba(148, 163, 184, 0.25)",
          borderWidth: 1,
          padding: 12,
          cornerRadius: 10,
          displayColors: false,
          callbacks: {
            title: function (items) {
              const it = items && items[0];
              if (!it) return "";
              // For scatter points x is index.
              const idx = typeof it.parsed.x === "number" ? it.parsed.x : it.dataIndex;
              return labels[idx] || it.label || "";
            },
            label: function (ctx) {
              if (ctx.dataset && ctx.dataset.label === "Events") {
                const raw = ctx.raw || {};
                const lbl = (raw.label || "").toString().trim();
                return lbl ? lbl : "Event";
              }
              return formatMoney(ctx.parsed.y);
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
              return Number(value).toFixed(2);
            },
          },
          grid: { color: "rgba(148, 163, 184, 0.1)" },
          border: { display: false },
        },
      },
    },
    plugins: [markerPlugin],
  });

  // Pointer cursor when hovering event points.
  canvas.addEventListener("mousemove", function (evt) {
    const points = chart.getElementsAtEventForMode(evt, "nearest", { intersect: true }, true);
    if (!points || !points.length) {
      canvas.style.cursor = "default";
      return;
    }
    const el = points[0];
    const ds = chart.data.datasets[el.datasetIndex];
    canvas.style.cursor = ds && ds.label === "Events" ? "pointer" : "default";
  });
})();
