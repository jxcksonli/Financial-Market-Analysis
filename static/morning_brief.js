(function () {
  const btn = document.getElementById("morning-brief-btn");
  const modal = document.getElementById("morning-brief-modal");
  const bodyEl = document.getElementById("brief-modal-body");
  const metaEl = document.getElementById("brief-modal-meta");
  const copyBtn = document.getElementById("brief-copy-btn");
  const exportBtn = document.getElementById("brief-export-btn");

  if (!btn || !modal || !bodyEl) return;

  let currentBrief = "";
  let currentDate = "";

  function openModal() {
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("brief-modal-open");
  }

  function closeModal() {
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("brief-modal-open");
  }

  function setLoading() {
    bodyEl.className = "brief-modal-body brief-modal-body--loading";
    bodyEl.textContent = "Building your morning brief…";
    if (metaEl) metaEl.textContent = "Fetching prices, news, and events";
    currentBrief = "";
    currentDate = "";
  }

  function setError(msg) {
    bodyEl.className = "brief-modal-body brief-modal-body--error";
    bodyEl.textContent = msg || "Could not generate brief.";
    if (metaEl) metaEl.textContent = "";
  }

  function renderBrief(text, dateStr, generatedAt) {
    currentBrief = text || "";
    currentDate = dateStr || new Date().toISOString().slice(0, 10);
    bodyEl.className = "brief-modal-body";
    bodyEl.textContent = currentBrief;

    if (metaEl) {
      const parts = [];
      if (dateStr) parts.push(dateStr);
      if (generatedAt) {
        try {
          const d = new Date(generatedAt);
          parts.push(
            "Generated " +
              d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
          );
        } catch {
          /* ignore */
        }
      }
      metaEl.textContent = parts.join(" · ");
    }
  }

  async function fetchBrief() {
    btn.disabled = true;
    openModal();
    setLoading();

    try {
      const res = await fetch("/api/morning-brief");
      const data = await res.json();

      if (!res.ok || !data.ok) {
        setError(data.error || "Request failed.");
        return;
      }

      renderBrief(data.brief, data.date, data.generated_at);
    } catch (e) {
      setError(e.message || "Network error.");
    } finally {
      btn.disabled = false;
    }
  }

  btn.addEventListener("click", fetchBrief);

  modal.querySelectorAll("[data-brief-close]").forEach(function (el) {
    el.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !modal.hidden) closeModal();
  });

  if (copyBtn) {
    copyBtn.addEventListener("click", async function () {
      if (!currentBrief) return;
      try {
        await navigator.clipboard.writeText(currentBrief);
        const prev = copyBtn.textContent;
        copyBtn.textContent = "Copied!";
        setTimeout(function () {
          copyBtn.textContent = prev;
        }, 1600);
      } catch {
        copyBtn.textContent = "Copy failed";
      }
    });
  }

  if (exportBtn) {
    exportBtn.addEventListener("click", function () {
      if (!currentBrief) return;
      const d = currentDate || new Date().toISOString().slice(0, 10);
      const filename = "morning-brief-" + d + ".txt";
      const blob = new Blob([currentBrief], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    });
  }
})();
