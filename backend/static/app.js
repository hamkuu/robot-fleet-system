const API_URL = "/api/v1/images";

const grid = document.querySelector("#image-grid");
const emptyState = document.querySelector("#empty-state");
const imageCount = document.querySelector("#image-count");
const uploadDialog = document.querySelector("#upload-dialog");
const editDialog = document.querySelector("#edit-dialog");
const uploadForm = document.querySelector("#upload-form");
const editForm = document.querySelector("#edit-form");
const toast = document.querySelector("#toast");

let images = [];
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3200);
}

async function request(url, options = {}) {
  const response = await fetch(url, options);

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : message;
    } catch {
      // Keep the status-based message for non-JSON responses.
    }
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function setLoading() {
  emptyState.hidden = true;
  grid.replaceChildren(...Array.from({ length: 3 }, () => {
    const skeleton = document.createElement("div");
    skeleton.className = "skeleton";
    return skeleton;
  }));
}

function makeButton(label, className, action, imageId) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.dataset.action = action;
  button.dataset.imageId = imageId;
  button.textContent = label;
  return button;
}

function addDetail(list, label, value, title = value) {
  const term = document.createElement("dt");
  term.textContent = label;

  const description = document.createElement("dd");
  description.textContent = value;
  description.title = title;

  list.append(term, description);
}

function makeCard(image) {
  const article = document.createElement("article");
  article.className = "image-card";

  const frame = document.createElement("div");
  frame.className = "image-frame";

  const preview = document.createElement("img");
  preview.src = `${API_URL}/${image.id}/content?v=${encodeURIComponent(image.updated_at)}`;
  preview.alt = image.filename;
  preview.loading = "lazy";

  frame.append(preview);

  const body = document.createElement("div");
  body.className = "card-body";

  const details = document.createElement("dl");
  details.className = "image-details";
  addDetail(details, "id", image.id);
  addDetail(details, "filename", image.filename);
  addDetail(details, "content_type", image.content_type);
  addDetail(details, "device_id", image.device_id);
  addDetail(details, "captured_at", formatDate(image.captured_at), image.captured_at);
  addDetail(details, "created_at", formatDate(image.created_at), image.created_at);
  addDetail(details, "updated_at", formatDate(image.updated_at), image.updated_at);
  addDetail(details, "metadata", JSON.stringify(image.metadata));

  const actions = document.createElement("div");
  actions.className = "card-actions";

  const view = document.createElement("a");
  view.className = "button button-secondary";
  view.href = `${API_URL}/${image.id}/content`;
  view.target = "_blank";
  view.rel = "noopener";
  view.textContent = "View";

  const download = document.createElement("a");
  download.className = "button button-secondary";
  download.href = `${API_URL}/${image.id}/content`;
  download.download = image.filename;
  download.textContent = "Download";

  const edit = makeButton("Edit", "button button-secondary", "edit", image.id);
  const remove = makeButton("Delete", "delete-button", "delete", image.id);
  remove.setAttribute("aria-label", `Delete ${image.filename}`);

  actions.append(view, download, edit, remove);
  body.append(details, actions);
  article.append(frame, body);
  return article;
}

function renderImages() {
  imageCount.textContent = images.length === 100 ? "100+" : String(images.length);
  emptyState.hidden = images.length !== 0;
  grid.hidden = images.length === 0;
  grid.replaceChildren(...images.map(makeCard));
}

async function loadImages({ loading = true } = {}) {
  if (loading) setLoading();
  try {
    images = await request(`${API_URL}?limit=100`);
    renderImages();
  } catch (error) {
    grid.replaceChildren();
    showToast(error.message);
  }
}

function localDateTimeValue(date = new Date()) {
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return offsetDate.toISOString().slice(0, 16);
}

function openUploadDialog() {
  uploadForm.reset();
  uploadForm.elements.metadata.value = "{}";
  document.querySelector("#captured-at").value = localDateTimeValue();
  document.querySelector("#upload-file-name").textContent = "JPEG, PNG or WebP · up to 10 MB";
  uploadDialog.showModal();
}

function parseMetadata(value) {
  const metadata = JSON.parse(value || "{}");
  if (!metadata || Array.isArray(metadata) || typeof metadata !== "object") {
    throw new Error("Metadata must be a JSON object");
  }
  return metadata;
}

document.querySelector("#open-upload").addEventListener("click", openUploadDialog);
document.querySelector("#empty-upload").addEventListener("click", openUploadDialog);
document.querySelector("#refresh").addEventListener("click", () => loadImages());

document.querySelector("#upload-image").addEventListener("change", (event) => {
  document.querySelector("#upload-file-name").textContent =
    event.target.files[0]?.name || "JPEG, PNG or WebP · up to 10 MB";
});

document.querySelectorAll(".close-dialog").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

[uploadDialog, editDialog].forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = uploadForm.querySelector('[type="submit"]');

  try {
    parseMetadata(uploadForm.elements.metadata.value);
    const formData = new FormData(uploadForm);
    formData.set("captured_at", new Date(uploadForm.elements.captured_at.value).toISOString());
    submit.disabled = true;
    await request(API_URL, { method: "POST", body: formData });
    uploadDialog.close();
    showToast("Capture published");
    await loadImages({ loading: false });
  } catch (error) {
    showToast(error instanceof SyntaxError ? "Metadata must be valid JSON" : error.message);
  } finally {
    submit.disabled = false;
  }
});

grid.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const image = images.find((candidate) => candidate.id === button.dataset.imageId);
  if (!image) return;

  if (button.dataset.action === "edit") {
    editForm.reset();
    editForm.elements.id.value = image.id;
    editForm.elements.filename.value = image.filename;
    editForm.elements.metadata.value = JSON.stringify(image.metadata, null, 2);
    editDialog.showModal();
    return;
  }

  if (button.dataset.action === "delete") {
    if (!window.confirm(`Delete “${image.filename}”? This cannot be undone.`)) return;
    try {
      button.disabled = true;
      await request(`${API_URL}/${image.id}`, { method: "DELETE" });
      images = images.filter((candidate) => candidate.id !== image.id);
      renderImages();
      showToast("Capture deleted");
    } catch (error) {
      button.disabled = false;
      showToast(error.message);
    }
  }
});

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submit = editForm.querySelector('[type="submit"]');
  const imageId = editForm.elements.id.value;

  try {
    const metadata = parseMetadata(editForm.elements.metadata.value);
    submit.disabled = true;
    await request(`${API_URL}/${imageId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: editForm.elements.filename.value, metadata }),
    });

    editDialog.close();
    showToast("Capture updated");
    await loadImages({ loading: false });
  } catch (error) {
    showToast(error instanceof SyntaxError ? "Metadata must be valid JSON" : error.message);
  } finally {
    submit.disabled = false;
  }
});

loadImages();
