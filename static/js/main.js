// main.js - landing page: drag & drop upload, then hand off to the backend.
(function () {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileListEl = document.getElementById("file-list");
  const analyzeBtn = document.getElementById("analyze-btn");
  const statusEl = document.getElementById("upload-status");

  let selectedFiles = [];

  function renderFileList() {
    fileListEl.innerHTML = "";
    selectedFiles.forEach((file) => {
      const li = document.createElement("li");
      li.innerHTML = `<i class="bi bi-file-earmark-pdf"></i> ${file.name}`;
      fileListEl.appendChild(li);
    });
    analyzeBtn.disabled = selectedFiles.length === 0;
  }

  function addFiles(fileArray) {
    const pdfsOnly = Array.from(fileArray).filter(
      (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
    );
    selectedFiles = selectedFiles.concat(pdfsOnly);
    renderFileList();
  }

  dropzone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => addFiles(e.target.files));

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add("mu-drag-over");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove("mu-drag-over");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files) {
      addFiles(e.dataTransfer.files);
    }
  });

  analyzeBtn.addEventListener("click", async () => {
    if (selectedFiles.length === 0) return;

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>Analyzing...`;
    statusEl.textContent = "Extracting text, running OCR where needed, and applying the NLP pipeline. This can take a little while for scanned papers.";

    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append("papers", file));

    try {
      const response = await fetch("/upload", { method: "POST", body: formData });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error || "Something went wrong.");
      }

      window.location.href = `/dashboard/${payload.run_id}`;
    } catch (err) {
      statusEl.textContent = "";
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = `<i class="bi bi-graph-up-arrow me-2"></i>Analyze Papers`;
      const alertEl = document.createElement("div");
      alertEl.className = "alert alert-danger mt-3 mb-0";
      alertEl.textContent = err.message;
      statusEl.parentElement.appendChild(alertEl);
    }
  });
})();
