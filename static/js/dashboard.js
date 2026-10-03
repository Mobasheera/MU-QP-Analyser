// dashboard.js - renders every widget on the analysis dashboard from the
// JSON payload embedded by the server, and wires up search + the
// per-question NLP inspect modal.
//
// The topic chart is drawn with the browser Canvas API instead of Chart.js.
// This keeps the dashboard self-contained and prevents an external CDN
// failure from stopping every widget below the chart.
(function () {
  const dataEl = document.getElementById("dashboard-data");
  if (!dataEl) return;

  let data;
  try {
    data = JSON.parse(dataEl.textContent || "{}");
  } catch (err) {
    console.error("Could not parse dashboard data", err);
    return;
  }

  const runId = data.run_id || "";

  // ---------------------------------------------------------------------
  // Topic frequency chart (dependency-free canvas renderer)
  // ---------------------------------------------------------------------
  const topicCanvas = document.getElementById("topic-chart");

  function cssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  function renderTopicChart() {
    if (!topicCanvas) return;

    const topics = Array.isArray(data.topics) ? data.topics : [];
    const rect = topicCanvas.getBoundingClientRect();
    const width = Math.max(320, Math.floor(rect.width || topicCanvas.parentElement?.clientWidth || 600));
    const height = 220;
    const dpr = window.devicePixelRatio || 1;

    topicCanvas.width = Math.floor(width * dpr);
    topicCanvas.height = Math.floor(height * dpr);
    topicCanvas.style.width = `${width}px`;
    topicCanvas.style.height = `${height}px`;

    const ctx = topicCanvas.getContext("2d");
    if (!ctx) return;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const ink = cssVar("--ink", "#16233B");
    const inkSoft = cssVar("--ink-soft", "#4B5768");
    const line = cssVar("--line", "#DEDCD1");
    const teal = cssVar("--teal", "#1F6F63");
    const surface = cssVar("--surface", "#FFFFFF");

    if (!topics.length) {
      ctx.fillStyle = inkSoft;
      ctx.font = '14px "IBM Plex Sans", sans-serif';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("No topic data available.", width / 2, height / 2);
      return;
    }

    // Keep the chart readable even when a paper produces many topic labels.
    const visibleTopics = topics.slice(0, 12);
    const maxCount = Math.max(1, ...visibleTopics.map((t) => Number(t.count) || 0));
    const left = Math.min(190, Math.max(110, Math.floor(width * 0.32)));
    const right = 44;
    const top = 8;
    const bottom = 8;
    const plotWidth = Math.max(100, width - left - right);
    const rowHeight = (height - top - bottom) / visibleTopics.length;
    const barHeight = Math.max(8, Math.min(18, rowHeight * 0.48));

    // Subtle vertical grid lines.
    ctx.strokeStyle = line;
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.75;
    for (let i = 0; i <= 4; i += 1) {
      const x = left + (plotWidth * i) / 4;
      ctx.beginPath();
      ctx.moveTo(x, top);
      ctx.lineTo(x, height - bottom);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    visibleTopics.forEach((topic, index) => {
      const count = Number(topic.count) || 0;
      const yCenter = top + rowHeight * index + rowHeight / 2;
      const barWidth = plotWidth * (count / maxCount);
      const y = yCenter - barHeight / 2;

      ctx.font = '12px "IBM Plex Sans", sans-serif';
      ctx.fillStyle = ink;
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(truncate(topic.topic || "Unclassified", 26), left - 10, yCenter);

      // Track.
      ctx.fillStyle = surface;
      roundRect(ctx, left, y, plotWidth, barHeight, 5);
      ctx.fill();

      // Bar.
      ctx.fillStyle = teal;
      roundRect(ctx, left, y, Math.max(barWidth, count ? 3 : 0), barHeight, 5);
      ctx.fill();

      ctx.font = '11px "IBM Plex Mono", monospace';
      ctx.fillStyle = inkSoft;
      ctx.textAlign = "left";
      ctx.fillText(String(count), left + plotWidth + 8, yCenter);
    });
  }

  function roundRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  renderTopicChart();
  window.addEventListener("resize", renderTopicChart);
  window.addEventListener("mu-theme-change", renderTopicChart);

  // ---------------------------------------------------------------------
  // N-grams
  // ---------------------------------------------------------------------
  function renderNgramList(elementId, items) {
    const el = document.getElementById(elementId);
    if (!el) return;

    items = Array.isArray(items) ? items : [];
    if (!items.length) {
      el.innerHTML = `<li class="text-muted">Not enough data yet.</li>`;
      return;
    }

    el.innerHTML = items
      .map((item) => `<li><span>${escapeHtml(item.phrase)}</span><span class="mu-ngram-count">${Number(item.count) || 0}&times;</span></li>`)
      .join("");
  }

  const ngrams = data.ngrams || {};
  renderNgramList("bigram-list", ngrams.bigrams);
  renderNgramList("trigram-list", ngrams.trigrams);

  // ---------------------------------------------------------------------
  // Repeated questions table
  // ---------------------------------------------------------------------
  const repeatedBody = document.querySelector("#repeated-table tbody");
  if (repeatedBody) {
    const pairs = Array.isArray(data.repeated_pairs) ? data.repeated_pairs : [];

    if (!pairs.length) {
      const paperCount = Number(data.stats?.paper_count) || 0;
      const message = paperCount < 2
        ? "Upload at least two papers to compare repeated questions across years."
        : "No repeated questions detected across the uploaded papers.";
      repeatedBody.innerHTML = `<tr><td colspan="5" class="text-muted">${message}</td></tr>`;
    } else {
      repeatedBody.innerHTML = pairs
        .map((pair) => {
          const a = pair.question_a || {};
          const b = pair.question_b || {};
          const score = Number(pair.similarity) || 0;
          const badgeClass = score >= 90 ? "text-bg-danger" : "text-bg-warning";
          return `<tr>
            <td>${escapeHtml(a.source_file || "Unknown")}<br><small class="text-muted">${escapeHtml(a.year || "Unknown")}</small></td>
            <td>${escapeHtml(truncate(a.text, 90))}</td>
            <td>${escapeHtml(b.source_file || "Unknown")}<br><small class="text-muted">${escapeHtml(b.year || "Unknown")}</small></td>
            <td>${escapeHtml(truncate(b.text, 90))}</td>
            <td><span class="badge ${badgeClass}">${score}%</span></td>
          </tr>`;
        })
        .join("");
    }
  }

  // ---------------------------------------------------------------------
  // Question grid (search + cards)
  // ---------------------------------------------------------------------
  const questionGrid = document.getElementById("question-grid");
  const searchInput = document.getElementById("search-input");
  let searchTimer = null;

  function sealLabel(question) {
    if (question.marks) return `${question.marks}m`;
    return question.label || "Q";
  }

  function renderQuestions(questions) {
    if (!questionGrid) return;

    questions = Array.isArray(questions) ? questions : [];
    if (!questions.length) {
      questionGrid.innerHTML = `<p class="text-muted">No questions match that search.</p>`;
      return;
    }

    questionGrid.innerHTML = questions
      .map(
        (q) => `
        <div class="mu-question-card" data-question-id="${escapeAttr(q.id || "")}">
          <div class="mu-question-seal">${escapeHtml(sealLabel(q))}</div>
          <span class="mu-question-topic">${escapeHtml(q.topic || "Unclassified")}</span>
          <p class="mu-question-text">${escapeHtml(truncate(q.text, 140))}</p>
          <div class="mu-question-meta">
            <span>${escapeHtml(q.label || "Question")} &middot; ${escapeHtml(q.source_file || "Unknown")}</span>
            <span>${escapeHtml(q.year || "Unknown")}</span>
          </div>
        </div>`
      )
      .join("");

    questionGrid.querySelectorAll(".mu-question-card").forEach((card) => {
      card.addEventListener("click", () => openInspectModal(card.dataset.questionId, questions));
    });
  }

  renderQuestions(Array.isArray(data.questions) ? data.questions : []);

  async function runSearch() {
    if (!searchInput) return;

    const query = searchInput.value.trim();
    if (!query) {
      renderQuestions(data.questions || []);
      return;
    }

    const modeEl = document.querySelector('input[name="search-mode"]:checked');
    const mode = modeEl ? modeEl.value : "keyword";

    try {
      const response = await fetch(`/api/search/${encodeURIComponent(runId)}?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(mode)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Search failed.");
      renderQuestions(payload.results || []);
    } catch (err) {
      console.error("Search failed", err);
      if (questionGrid) {
        questionGrid.innerHTML = `<p class="text-danger">Search failed. Please try again.</p>`;
      }
    }
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(runSearch, 300);
    });
  }

  document.querySelectorAll('input[name="search-mode"]').forEach((el) => {
    el.addEventListener("change", runSearch);
  });

  // ---------------------------------------------------------------------
  // Per-question NLP inspect modal (stages 1-7, on demand)
  // ---------------------------------------------------------------------
  const modalEl = document.getElementById("question-modal");
  const modalBody = document.getElementById("question-modal-body");
  const modalLabel = document.getElementById("question-modal-label");
  let bsModal = null;

  if (modalEl && window.bootstrap && typeof window.bootstrap.Modal === "function") {
    bsModal = new window.bootstrap.Modal(modalEl);
  }

  async function openInspectModal(questionId, questionPool) {
    const pool = Array.isArray(questionPool) ? questionPool : [];
    const question = pool.find((q) => q.id === questionId) || (data.questions || []).find((q) => q.id === questionId);

    if (modalLabel) {
      modalLabel.textContent = question ? `${question.label || "Question"} · ${question.topic || "Unclassified"}` : "Question";
    }
    if (modalBody) {
      modalBody.innerHTML = `<div class="text-center py-4"><div class="spinner-border" role="status"></div></div>`;
    }

    if (bsModal) {
      bsModal.show();
    } else if (modalEl) {
      // Graceful fallback if Bootstrap JS is unavailable.
      modalEl.classList.add("show");
      modalEl.style.display = "block";
      modalEl.removeAttribute("aria-hidden");
    }

    try {
      const response = await fetch(`/api/question/${encodeURIComponent(runId)}/${encodeURIComponent(questionId)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load analysis.");
      renderInspectModal(payload.question, payload.analysis);
    } catch (err) {
      if (modalBody) {
        modalBody.innerHTML = `<div class="alert alert-danger mb-0">${escapeHtml(err.message)}</div>`;
      }
    }
  }

  function renderInspectModal(question, analysis) {
    if (!modalBody) return;
    analysis = analysis || {};

    const pillList = (items) => {
      items = Array.isArray(items) ? items : [];
      return items.length
        ? items.map((t) => `<span class="mu-token-pill">${escapeHtml(t)}</span>`).join("")
        : `<span class="text-muted">None</span>`;
    };

    const posTable = (analysis.pos_tags || [])
      .map((p) => `<tr><td>${escapeHtml(p.token)}</td><td>${escapeHtml(p.pos)}</td><td>${escapeHtml(p.explanation)}</td></tr>`)
      .join("");

    const morphTable = (analysis.morphology || [])
      .map((m) => `<tr><td>${escapeHtml(m.token)}</td><td>${escapeHtml(m.lemma)}</td><td>${escapeHtml(m.stem)}</td><td>${escapeHtml(m.pos)}</td><td>${escapeHtml(m.morphology)}</td></tr>`)
      .join("");

    const entities = Array.isArray(analysis.entities) ? analysis.entities : [];
    const entityPills = entities.length
      ? entities.map((e) => `<span class="mu-token-pill">${escapeHtml(e.text)} <em>(${escapeHtml(e.label)})</em></span>`).join("")
      : `<span class="text-muted">None detected</span>`;

    const chunks = analysis.chunks || {};
    const questionKeywords = Array.isArray(question?.keywords) ? question.keywords : [];
    const tokens = Array.isArray(analysis.tokens) ? analysis.tokens : [];
    const tokensNoStopwords = Array.isArray(analysis.tokens_no_stopwords) ? analysis.tokens_no_stopwords : [];

    modalBody.innerHTML = `
      <p class="fw-semibold">${escapeHtml(question?.text || "")}</p>

      <div class="mu-inspect-section">
        <h6>1·2 · Tokens &amp; Stopword Removal</h6>
        <div>${pillList(questionKeywords)}</div>
        <p class="small text-muted mt-2 mb-1">All tokens:</p>
        <div>${pillList(tokens)}</div>
        <p class="small text-muted mt-2 mb-1">After stopword removal:</p>
        <div>${pillList(tokensNoStopwords)}</div>
      </div>

      <div class="mu-inspect-section">
        <h6>3·4 · Lemmatization, Porter Stemming &amp; Morphological Analysis</h6>
        <div class="table-responsive">
          <table class="mu-morph-table">
            <thead><tr><th>Token</th><th>Lemma</th><th>Stem</th><th>POS</th><th>Morphology</th></tr></thead>
            <tbody>${morphTable}</tbody>
          </table>
        </div>
      </div>

      <div class="mu-inspect-section">
        <h6>5 · POS Tagging</h6>
        <div class="table-responsive">
          <table class="mu-morph-table">
            <thead><tr><th>Token</th><th>Tag</th><th>Meaning</th></tr></thead>
            <tbody>${posTable}</tbody>
          </table>
        </div>
      </div>

      <div class="mu-inspect-section">
        <h6>6 · Chunking</h6>
        <p class="small text-muted mb-1">Noun phrases:</p>
        <div>${pillList(chunks.noun_phrases)}</div>
        <p class="small text-muted mt-2 mb-1">Verb phrases:</p>
        <div>${pillList(chunks.verb_phrases)}</div>
      </div>

      <div class="mu-inspect-section mb-0">
        <h6>7 · Named Entity Recognition</h6>
        <div>${entityPills}</div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------
  function truncate(text, maxLen) {
    if (!text) return "";
    text = String(text);
    return text.length > maxLen ? text.slice(0, maxLen).trim() + "…" : text;
  }

  function escapeHtml(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function escapeAttr(str) {
    return escapeHtml(str);
  }
})();
