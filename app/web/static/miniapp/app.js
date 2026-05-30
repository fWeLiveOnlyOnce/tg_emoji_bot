const tg = window.Telegram?.WebApp ?? null;

const state = {
  user: null,
  currentJob: null,
  pollTimer: null,
  selectedOrientation: null,
  selectedGrid: null,
};

function getInitData() {
  return tg?.initData || "";
}

function ensureTelegramContext() {
  const initData = getInitData();
  if (!initData) {
    throw new Error("Пустой initData. Открой приложение из Telegram.");
  }
  return initData;
}

async function apiFetch(path, options = {}) {
  const initData = ensureTelegramContext();

  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `TelegramInitData ${initData}`);

  const response = await fetch(path, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const message =
      (isJson && (payload.detail || payload.error)) ||
      (typeof payload === "string" ? payload : `HTTP ${response.status}`);
    throw new Error(message);
  }

  return payload;
}

async function authMiniApp() {
  const initData = ensureTelegramContext();

  const response = await fetch("/api/miniapp/auth", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      init_data: initData,
    }),
  });

  const payload = await response.json();

  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || payload.detail || "Ошибка авторизации");
  }

  state.user = payload.user;
  return payload;
}

async function createJob({ title, orientation, gridCode }) {
  return apiFetch("/api/miniapp/jobs", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title,
      orientation,
      grid_code: gridCode,
    }),
  });
}

async function uploadJobFile(publicId, file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch(`/api/miniapp/jobs/${publicId}/upload`, {
    method: "POST",
    body: formData,
  });
}

async function updateJob(publicId, { title, orientation, gridCode }) {
  return apiFetch(`/api/miniapp/jobs/${publicId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      title,
      orientation,
      grid_code: gridCode,
    }),
  });
}

async function startJob(publicId) {
  return apiFetch(`/api/miniapp/jobs/${publicId}/start`, {
    method: "POST",
  });
}

async function fetchJob(publicId) {
  return apiFetch(`/api/miniapp/jobs/${publicId}`, {
    method: "GET",
  });
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

function renderUser(user) {
  const el = document.querySelector("[data-user]");
  if (!el || !user) return;
  el.textContent = user.display_name || user.username || `ID ${user.id}`;
}

function renderStatus(message, kind = "info") {
  const el = document.querySelector("[data-status]");
  if (!el) return;
  el.textContent = message;
  el.dataset.kind = kind;
}

function renderJob(job) {
  const box = document.querySelector("[data-job-result]");
  if (!box) return;

  box.hidden = false;
  box.innerHTML = `
    <div><strong>Пак:</strong> ${job.title ?? "-"}</div>
    <div><strong>ID:</strong> ${job.public_id}</div>
    <div><strong>Статус:</strong> ${job.status}</div>
    <div><strong>Short name:</strong> ${job.short_name ?? "-"}</div>
    <div><strong>Ориентация:</strong> ${job.orientation ?? "-"}</div>
    <div><strong>Сетка:</strong> ${job.grid_code ?? "-"}</div>
    <div><strong>URL:</strong> ${
      job.pack_url
        ? `<a href="${job.pack_url}" target="_blank" rel="noopener noreferrer">Открыть пак</a>`
        : "-"
    }</div>
    <div><strong>Ошибка:</strong> ${job.error_message ?? "-"}</div>
  `;
}

function applyOrientationOptions(orientation) {
  state.selectedOrientation = orientation;

  document.querySelectorAll("[data-orientation]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.orientation === orientation);
  });

  const gridButtons = document.querySelectorAll("[data-grid]");
  gridButtons.forEach((button) => {
    const allowed = (button.dataset.allowedOrientations || "")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

    if (allowed.length === 0) {
      button.hidden = false;
      button.disabled = false;
      return;
    }

    const isAllowed = allowed.includes(orientation);
    button.hidden = !isAllowed;
    button.disabled = !isAllowed;

    if (!isAllowed && state.selectedGrid === button.dataset.grid) {
      state.selectedGrid = null;
      button.classList.remove("is-active");
    }
  });
}

function applyGridSelection(gridCode) {
  state.selectedGrid = gridCode;

  document.querySelectorAll("[data-grid]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.grid === gridCode);
  });
}

function startPolling(publicId) {
  stopPolling();

  state.pollTimer = setInterval(async () => {
    try {
      const job = await fetchJob(publicId);
      state.currentJob = job;
      renderJob(job);
      renderStatus(`Текущий статус: ${job.status}`, "info");

      if (["done", "failed", "cancelled"].includes(job.status)) {
        stopPolling();

        if (job.status === "done") {
          renderStatus("Задача завершена.", "success");
        } else {
          renderStatus(`Задача завершилась со статусом ${job.status}.`, "error");
        }
      }
    } catch (error) {
      stopPolling();
      renderStatus(error.message || "Ошибка при обновлении статуса", "error");
    }
  }, 2500);
}

async function handleCreateClick() {
  const titleInput = document.querySelector("[data-pack-title]");
  const fileInput = document.querySelector("[data-pack-file]");
  const createButton = document.querySelector("[data-create-pack]");

  const title = titleInput?.value?.trim() || "";
  const file = fileInput?.files?.[0] || null;
  const orientation = state.selectedOrientation;
  const gridCode = state.selectedGrid;

  if (!file) {
    renderStatus("Сначала выбери файл.", "error");
    return;
  }

  if (!title) {
    renderStatus("Введите название пака.", "error");
    return;
  }

  if (!orientation) {
    renderStatus("Выберите ориентацию.", "error");
    return;
  }

  if (!gridCode) {
    renderStatus("Выберите сетку.", "error");
    return;
  }

  createButton?.setAttribute("disabled", "disabled");

  try {
    renderStatus("Создаю задачу…", "info");

    const createdJob = await createJob({
      title,
      orientation,
      gridCode,
    });

    state.currentJob = createdJob;
    renderJob(createdJob);

    renderStatus("Загружаю файл…", "info");
    const uploadedJob = await uploadJobFile(createdJob.public_id, file);
    state.currentJob = uploadedJob;
    renderJob(uploadedJob);

    renderStatus("Сохраняю параметры…", "info");
    const updatedJob = await updateJob(createdJob.public_id, {
      title,
      orientation,
      gridCode,
    });
    state.currentJob = updatedJob;
    renderJob(updatedJob);

    renderStatus("Ставлю задачу в очередь…", "info");
    const startedJob = await startJob(createdJob.public_id);
    state.currentJob = startedJob;
    renderJob(startedJob);

    renderStatus(`Задача создана. Статус: ${startedJob.status}`, "success");
    startPolling(startedJob.public_id);
  } catch (error) {
    renderStatus(error.message || "Не удалось создать задачу", "error");
    console.error(error);
  } finally {
    createButton?.removeAttribute("disabled");
  }
}

function bindUi() {
  document.querySelectorAll("[data-orientation]").forEach((button) => {
    button.addEventListener("click", () => {
      applyOrientationOptions(button.dataset.orientation);
    });
  });

  document.querySelectorAll("[data-grid]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.disabled || button.hidden) return;
      applyGridSelection(button.dataset.grid);
    });
  });

  const createButton = document.querySelector("[data-create-pack]");
  createButton?.addEventListener("click", handleCreateClick);
}

async function bootstrap() {
  if (tg) {
    tg.ready();
    tg.expand();
  }

  bindUi();

  try {
    const auth = await authMiniApp();
    renderUser(auth.user);

    if (!state.selectedOrientation) {
      const firstOrientation = document.querySelector("[data-orientation]")?.dataset.orientation;
      if (firstOrientation) {
        applyOrientationOptions(firstOrientation);
      }
    }

    renderStatus("Mini App авторизован.", "success");
  } catch (error) {
    renderStatus(error.message || "Ошибка инициализации Mini App", "error");
    console.error(error);
  }
}

document.addEventListener("DOMContentLoaded", bootstrap);