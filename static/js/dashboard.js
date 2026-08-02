// dashboard.js - renders every widget on the analysis dashboard from the
// JSON payload embedded by the server, and wires up search + the
// per-question NLP inspect modal.
(function () {
  const data = JSON.parse(document.getElementById("dashboard-data").textContent);
  const runId = data.run_id;

  const chartColors = ["#1F6F63", "#E0982A", "#B23A48", "#4B5768", "#7ED1C2", "#C97B2E"];

  // ---------------------------------------------------------------------
  // Topic frequency chart
  // ---------------------------------------------------------------------
  const topicCtx = document.getElementById("topic-chart");
  if (topicCtx && data.topics.length) {
    new Chart(topicCtx, {
      type: "bar",
      data: {
        labels: data.topics.map((t) => t.topic),
        datasets: [
          {
            label: "Questions",
            data: data.topics.map((t) => t.count),
            backgroundColor: "#1F6F63",
            borderRadius: 6,
            maxBarThickness: 34,
          },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  // ---------------------------------------------------------------------
  // N-grams
  // ---------------------------------------------------------------------
  function renderNgramList(elementId, items) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (!items.length) {
      el.innerHTML = `<li class="text-muted">Not enough data yet.</li>`;
      return;
    }
    el.innerHTML = items
      .map((item) => `<li><span>${item.phrase}</span><span class="mu-ngram-count">${item.count}&times;</span></li>`)
      .join("");
  }
  renderNgramList("bigram-list", data.ngrams.bigrams);
  renderNgramList("trigram-list", data.ngrams.trigrams);

  // ---------------------------------------------------------------------
  // Repeated questions table
  // ---------------------------------------------------------------------
  const repeatedBody = document.querySelector("#repeated-table tbody");
  if (repeatedBody) {
    if (!data.repeated_pairs.length) {
      repeatedBody.innerHTML = `<tr><td colspan="5" class="text-muted">No repeated questions detected across the uploaded papers.</td></tr>`;
    } else {
      repeatedBody.innerHTML = data.repeated_pairs
        .map((pair) => {
          const a = pair.question_a, b = pair.question_b;
          const badgeClass = pair.similarity >= 90 ? "text-bg-danger" : "text-bg-warning";
          return `<tr>
            <td>${escapeHtml(a.source_file)}<br><small class="text-muted">${a.year}</small></td>
            <td>${escapeHtml(truncate(a.text, 90))}</td>
            <td>${escapeHtml(b.source_file)}<br><small class="text-muted">${b.year}</small></td>
            <td>${escapeHtml(truncate(b.text, 90))}</td>
            <td><span class="badge ${badgeClass}">${pair.similarity}%</span></td>
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
    return question.label;
  }

  function renderQuestions(questions) {
    if (!questions.length) {
      questionGrid.innerHTML = `<p class="text-muted">No questions match that search.</p>`;
      return;
    }
    questionGrid.innerHTML = questions
      .map(
        (q) => `
        <div class="mu-question-card" data-question-id="${escapeAttr(q.id)}">
          <div class="mu-question-seal">${escapeHtml(sealLabel(q))}</div>
          <span class="mu-question-topic">${escapeHtml(q.topic || "Unclassified")}</span>
          <p class="mu-question-text">${escapeHtml(truncate(q.text, 140))}</p>
          <div class="mu-question-meta">
            <span>${escapeHtml(q.label)} &middot; ${escapeHtml(q.source_file)}</span>
            <span>${escapeHtml(q.year)}</span>
          </div>
        </div>`
      )
      .join("");

    questionGrid.querySelectorAll(".mu-question-card").forEach((card) => {
      card.addEventListener("click", () => openInspectModal(card.dataset.questionId, questions));
    });
  }

  renderQuestions(data.questions);

  async function runSearch() {
    const query = searchInput.value.trim();
    if (!query) {
      renderQuestions(data.questions);
      return;
    }
    const mode = document.querySelector('input[name="search-mode"]:checked').value;
    try {
      const response = await fetch(`/api/search/${runId}?q=${encodeURIComponent(query)}&mode=${mode}`);
      const payload = await response.json();
      renderQuestions(payload.results || []);
    } catch (err) {
      console.error("Search failed", err);
    }
  }

  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 300);
  });
  document.querySelectorAll('input[name="search-mode"]').forEach((el) => {
    el.addEventListener("change", runSearch);
  });

  // ---------------------------------------------------------------------
  // Per-question NLP inspect modal (stages 1-7, on demand)
  // ---------------------------------------------------------------------
  const modalEl = document.getElementById("question-modal");
  const modalBody = document.getElementById("question-modal-body");
  const modalLabel = document.getElementById("question-modal-label");
  const bsModal = new bootstrap.Modal(modalEl);

  async function openInspectModal(questionId, questionPool) {
    const question = questionPool.find((q) => q.id === questionId) || data.questions.find((q) => q.id === questionId);
    modalLabel.textContent = question ? `${question.label} &middot; ${question.topic}`.replace("&middot;", "\u00b7") : "Question";
    modalBody.innerHTML = `<div class="text-center py-4"><div class="spinner-border" role="status"></div></div>`;
    bsModal.show();

    try {
      const response = await fetch(`/api/question/${runId}/${encodeURIComponent(questionId)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not load analysis.");
      renderInspectModal(payload.question, payload.analysis);
    } catch (err) {
      modalBody.innerHTML = `<div class="alert alert-danger mb-0">${escapeHtml(err.message)}</div>`;
    }
  }

  function renderInspectModal(question, analysis) {
    const pillList = (items) =>
      items.length
        ? items.map((t) => `<span class="mu-token-pill">${escapeHtml(t)}</span>`).join("")
        : `<span class="text-muted">None</span>`;

    const posTable = analysis.pos_tags
      .map((p) => `<tr><td>${escapeHtml(p.token)}</td><td>${escapeHtml(p.pos)}</td><td>${escapeHtml(p.explanation)}</td></tr>`)
      .join("");

    const morphTable = analysis.morphology
      .map((m) => `<tr><td>${escapeHtml(m.token)}</td><td>${escapeHtml(m.lemma)}</td><td>${escapeHtml(m.stem)}</td><td>${escapeHtml(m.pos)}</td><td>${escapeHtml(m.morphology)}</td></tr>`)
      .join("");

    const entityPills = analysis.entities.length
      ? analysis.entities.map((e) => `<span class="mu-token-pill">${escapeHtml(e.text)} <em>(${escapeHtml(e.label)})</em></span>`).join("")
      : `<span class="text-muted">None detected</span>`;

    modalBody.innerHTML = `
      <p class="fw-semibold">${escapeHtml(question.text)}</p>

      <div class="mu-inspect-section">
        <h6>1&middot;2 &middot; Tokens &amp; Stopword Removal</h6>
        <div>${pillList(question.keywords && question.keywords.length ? question.keywords : [])}</div>
        <p class="small text-muted mt-2 mb-1">All tokens:</p>
        <div>${pillList(analysis.tokens)}</div>
        <p class="small text-muted mt-2 mb-1">After stopword removal:</p>
        <div>${pillList(analysis.tokens_no_stopwords)}</div>
      </div>

      <div class="mu-inspect-section">
        <h6>3&middot;4 &middot; Lemmatization, Porter Stemming &amp; Morphological Analysis</h6>
        <div class="table-responsive">
          <table class="mu-morph-table">
            <thead><tr><th>Token</th><th>Lemma</th><th>Stem</th><th>POS</th><th>Morphology</th></tr></thead>
            <tbody>${morphTable}</tbody>
          </table>
        </div>
      </div>

      <div class="mu-inspect-section">
        <h6>5 &middot; POS Tagging</h6>
        <div class="table-responsive">
          <table class="mu-morph-table">
            <thead><tr><th>Token</th><th>Tag</th><th>Meaning</th></tr></thead>
            <tbody>${posTable}</tbody>
          </table>
        </div>
      </div>

      <div class="mu-inspect-section">
        <h6>6 &middot; Chunking</h6>
        <p class="small text-muted mb-1">Noun phrases:</p>
        <div>${pillList(analysis.chunks.noun_phrases)}</div>
        <p class="small text-muted mt-2 mb-1">Verb phrases:</p>
        <div>${pillList(analysis.chunks.verb_phrases)}</div>
      </div>

      <div class="mu-inspect-section mb-0">
        <h6>7 &middot; Named Entity Recognition</h6>
        <div>${entityPills}</div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------
  function truncate(text, maxLen) {
    if (!text) return "";
    return text.length > maxLen ? text.slice(0, maxLen).trim() + "…" : text;
  }
  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
  function escapeAttr(str) {
    return escapeHtml(str);
  }
})();
