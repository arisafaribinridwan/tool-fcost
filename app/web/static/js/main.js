(function () {
  const stampEl = document.getElementById("build-stamp");
  const formEl = document.getElementById("execute-form");
  const sourceInputEl = document.getElementById("source-file");
  const configSelectEl = document.getElementById("config-select");
  const executeBtnEl = document.getElementById("execute-btn");
  const errorEl = document.getElementById("form-error");
  const logListEl = document.getElementById("process-log");
  const resultStateEl = document.getElementById("result-state");

  if (
    !stampEl ||
    !formEl ||
    !sourceInputEl ||
    !configSelectEl ||
    !executeBtnEl ||
    !errorEl ||
    !logListEl ||
    !resultStateEl
  ) {
    return;
  }

  const now = new Date();
  const formatted = new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(now);

  stampEl.textContent = `Local app ready at ${formatted}`;

  void initializeConfigOptions();

  formEl.addEventListener("submit", (event) => {
    event.preventDefault();
    clearError();

    const selectedFile = sourceInputEl.files?.[0] ?? null;
    const selectedConfig = configSelectEl.value.trim();
    const validationError = validateInput(selectedFile, selectedConfig);
    if (validationError) {
      showError(validationError);
      addLog(validationError, "error");
      return;
    }

    void executeDryRun(selectedFile, selectedConfig);
  });

  async function initializeConfigOptions() {
    try {
      const response = await fetch("/api/configs");
      const payload = await response.json();
      const configNames = Array.isArray(payload.configs) ? payload.configs : [];
      populateConfigSelect(configNames);
      if (configNames.length === 0) {
        addLog("Belum ada file YAML pada folder configs/.", "info");
      }
    } catch (error) {
      populateConfigSelect([]);
      showError("Gagal memuat daftar config. Periksa koneksi lokal aplikasi.");
      addLog("Gagal memuat config list dari backend.", "error");
    }
  }

  function populateConfigSelect(configNames) {
    configSelectEl.innerHTML = "";
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent =
      configNames.length > 0
        ? "Pilih file config YAML"
        : "Tidak ada config YAML tersedia";
    configSelectEl.append(defaultOption);

    for (const configName of configNames) {
      const optionEl = document.createElement("option");
      optionEl.value = configName;
      optionEl.textContent = configName;
      configSelectEl.append(optionEl);
    }
  }

  function validateInput(selectedFile, selectedConfig) {
    if (!selectedFile) {
      return "File source wajib dipilih terlebih dulu.";
    }
    const lowerName = selectedFile.name.toLowerCase();
    const isAllowedExtension = lowerName.endsWith(".xlsx") || lowerName.endsWith(".csv");
    if (!isAllowedExtension) {
      return "Ekstensi file source harus .xlsx atau .csv.";
    }
    if (!selectedConfig) {
      return "Config YAML wajib dipilih.";
    }
    return null;
  }

  async function executeDryRun(selectedFile, selectedConfig) {
    setBusyState(true);
    addLog("Menjalankan dry-run pipeline...", "info");

    const formData = new FormData();
    formData.append("source_file", selectedFile);
    formData.append("config_name", selectedConfig);

    try {
      const response = await fetch("/api/execute", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        const backendError = typeof payload.error === "string" ? payload.error : "Execute gagal.";
        showError(backendError);
        addLog(backendError, "error");
        return;
      }

      clearLogList();
      if (Array.isArray(payload.logs)) {
        for (const entry of payload.logs) {
          const level = typeof entry.level === "string" ? entry.level : "info";
          const message = typeof entry.message === "string" ? entry.message : "Log entry";
          addLog(message, level, entry.time);
        }
      }

      renderResult(payload);
    } catch (error) {
      showError("Terjadi kesalahan jaringan saat execute.");
      addLog("Execute gagal karena masalah jaringan lokal.", "error");
    } finally {
      setBusyState(false);
    }
  }

  function renderResult(payload) {
    const result = payload?.result ?? {};
    const fileName = typeof result.file_name === "string" ? result.file_name : "-";
    const mode = typeof payload.mode === "string" ? payload.mode : "unknown";
    const runId = typeof payload.run_id === "string" ? payload.run_id : "-";
    const downloadUrl = typeof result.download_url === "string" ? result.download_url : null;
    const downloadReady = result.download_ready === true;

    resultStateEl.innerHTML = "";

    const titleEl = document.createElement("p");
    titleEl.className = "result-title";
    titleEl.textContent = `Run ${runId} selesai`;

    const fileEl = document.createElement("p");
    fileEl.className = "result-meta";
    fileEl.textContent = `Output name: ${fileName}`;

    const modeEl = document.createElement("p");
    modeEl.className = "result-meta";
    modeEl.textContent = `Mode: ${mode} (belum menulis file final di fase 2)`;

    const downloadButtonEl = document.createElement("button");
    downloadButtonEl.type = "button";
    downloadButtonEl.textContent = downloadReady ? "Download output" : "Download output (coming soon)";
    if (downloadReady && downloadUrl) {
      downloadButtonEl.addEventListener("click", () => {
        window.location.href = downloadUrl;
      });
    } else {
      downloadButtonEl.disabled = true;
    }

    resultStateEl.append(titleEl, fileEl, modeEl, downloadButtonEl);
  }

  function addLog(message, level, isoTime) {
    const liEl = document.createElement("li");
    liEl.className = "log-item";
    liEl.dataset.level = level;

    const stampEl = document.createElement("span");
    stampEl.className = "log-time";
    const timeText = formatTime(isoTime);
    stampEl.textContent = `[${timeText}]`;

    const textEl = document.createElement("span");
    textEl.textContent = message;

    liEl.append(stampEl, textEl);
    logListEl.prepend(liEl);
  }

  function clearLogList() {
    logListEl.innerHTML = "";
  }

  function formatTime(isoTime) {
    const date = isoTime ? new Date(isoTime) : new Date();
    if (Number.isNaN(date.getTime())) {
      return "time-n/a";
    }
    return new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(date);
  }

  function showError(message) {
    errorEl.textContent = message;
    errorEl.hidden = false;
  }

  function clearError() {
    errorEl.textContent = "";
    errorEl.hidden = true;
  }

  function setBusyState(isBusy) {
    executeBtnEl.disabled = isBusy;
    executeBtnEl.textContent = isBusy ? "Executing..." : "Execute";
  }
})();
