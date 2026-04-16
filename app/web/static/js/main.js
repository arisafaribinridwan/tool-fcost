(function () {
  const stampEl = document.getElementById("build-stamp");
  if (!stampEl) {
    return;
  }

  const now = new Date();
  const formatted = new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(now);

  stampEl.textContent = `Local app ready at ${formatted}`;
})();
