// theme.js - dark mode toggle, persisted across visits.
(function () {
  const root = document.documentElement;
  const toggleBtn = document.getElementById("theme-toggle");
  const STORAGE_KEY = "mu-nlp-theme";

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    if (toggleBtn) {
      const icon = toggleBtn.querySelector("i");
      if (icon) {
        icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
      }
    }

    // Let dashboard widgets that draw on canvas (rather than depending on a
    // third-party chart library) repaint themselves when the theme changes.
    window.dispatchEvent(new CustomEvent("mu-theme-change", { detail: { theme } }));
  }

  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "light" || saved === "dark") {
    applyTheme(saved);
  } else if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
    applyTheme("dark");
  } else {
    applyTheme("light");
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      const current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      const next = current === "dark" ? "light" : "dark";
      applyTheme(next);
      localStorage.setItem(STORAGE_KEY, next);
    });
  }
})();
