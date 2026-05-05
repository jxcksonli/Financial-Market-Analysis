(function () {
  const el = document.getElementById("ticker-chart-data");
  const metaEl = document.getElementById("ticker-meta-json");
  if (!el || typeof Chart === "undefined") return;

  let series;
  try {
    series = JSON.parse(el.textContent || "[]");
  } catch {
    return;
  }
  if (!Array.isArray(series) || !series.length) return;

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

  new Chart(canvas, {
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
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
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
            label: function (ctx) {
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
  });
})();
