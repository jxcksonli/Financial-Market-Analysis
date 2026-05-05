(function () {
  const form = document.getElementById("lookup-form");
  const submitBtn = document.getElementById("submit-btn");
  if (!form || !submitBtn) return;

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
})();
