const state = {
  media: [],
  folders: [],
  remoteLibraries: [],
  queue: [],
  current: null,
  currentIndex: -1,
  repeat: "none",
  selectedPlaylist: null,
  playlists: [],
  playlistDraft: [],
  invalidMedia: { count: 0, items: [] },
  view: "folders",
  playlistDirty: false,
  bulkBusy: false,
  activeRemoteLibrary: "",
  mediaPage: 1,
  mediaPageSize: 50,
  mediaTotal: 0,
  mediaTotalAll: 0,
  mediaTotalPages: 1,
  mediaLoading: false,
  mediaError: "",
  mediaRequestSeq: 0,
  filterTimer: null,
  bpmAnalyzeTimer: null,
  bpmPollTimer: null,
  playlistPage: 1,
  playlistPageSize: 50,
  playlistFilteredTotal: 0,
  trackImportToken: "",
  playlistImportToken: "",
};

const $ = (id) => document.getElementById(id);
const audio = $("audio");
const video = $("video");
const BUILD_STAMP = "2026-07-19T10:45:00+09:00";
window.__jinnDebug = [];

function debugLog(label, data = {}) {
  const entry = { label, data, at: new Date().toISOString() };
  window.__jinnDebug.push(entry);
  let rendered = "";
  try {
    rendered = JSON.stringify(data);
  } catch {
    rendered = String(data);
  }
  console.log("[JinnSP]", label, rendered, data);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function fmtTime(value) {
  if (!Number.isFinite(value)) return "0:00";
  const mins = Math.floor(value / 60);
  const secs = Math.floor(value % 60).toString().padStart(2, "0");
  return `${mins}:${secs}`;
}

async function api(path, options = {}) {
  const method = options.method || "GET";
  debugLog("api:start", { path, method, body: options.body || "" });
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  debugLog("api:response", { path, method, status: res.status, ok: res.ok, body: data });
  if (!res.ok) {
    throw new Error(data.error || data.raw || `HTTP ${res.status}`);
  }
  return data;
}

async function requestFormJson(path, formData) {
  debugLog("form:start", { path });
  const res = await fetch(path, { method: "POST", body: formData });
  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  debugLog("form:response", { path, status: res.status, ok: res.ok, body: data });
  if (!res.ok) throw new Error(data.error || data.raw || `HTTP ${res.status}`);
  return data;
}

function csvFilenameFromDisposition(disposition, fallbackName) {
  const header = disposition || "";
  const star = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim().replace(/^"|"$/g, ""));
    } catch {
      return star[1].trim().replace(/^"|"$/g, "") || fallbackName;
    }
  }
  const normal = header.match(/filename="?([^";]+)"?/i);
  return normal ? normal[1].trim() : fallbackName;
}

async function downloadCsv(url, fallbackName, statusId = "exportStatus") {
  const statusEl = $(statusId);
  if (statusEl) statusEl.textContent = "Exporting CSV...";
  debugLog("csv:export:start", { url });
  const response = await fetch(url);
  const textForError = response.ok ? "" : await response.text();
  debugLog("csv:export:response", {
    url,
    status: response.status,
    ok: response.ok,
    contentType: response.headers.get("Content-Type") || "",
    contentDisposition: response.headers.get("Content-Disposition") || "",
  });
  if (!response.ok) {
    const message = `Export failed: HTTP ${response.status}${textForError ? ` ${textForError}` : ""}`;
    if (statusEl) statusEl.textContent = message;
    throw new Error(message);
  }

  const blob = await response.blob();
  const filename = csvFilenameFromDisposition(response.headers.get("Content-Disposition"), fallbackName);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  if (statusEl) statusEl.textContent = `Saved ${filename}`;
  return { filename, size: blob.size };
}

function filtersQuery() {
  const params = new URLSearchParams();
  for (const [key, id] of [
    ["q", "q"],
    ["media_type", "mediaType"],
    ["source_type", "sourceType"],
    ["genre", "genre"],
    ["tag", "tag"],
    ["bpm_min", "bpmMin"],
    ["bpm_max", "bpmMax"],
    ["rating", "rating"],
  ]) {
    const value = $(id).value;
    if (value) params.set(key, value);
  }
  if (state.activeRemoteLibrary) params.set("remote_library", state.activeRemoteLibrary);
  return params;
}

function itemsFromResponse(response) {
  return Array.isArray(response) ? response : (response.items || []);
}

function pageLabel(page, totalPages) {
  return `Page ${page} / ${totalPages || 1}`;
}

function showingLabel(page, pageSize, total) {
  if (!total) return "Showing 0";
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(total, page * pageSize);
  return `Showing ${start}-${end} of ${total}`;
}

function activeFilterSummary() {
  const entries = [
    ["Search", $("q").value],
    ["Media type", $("mediaType").selectedOptions[0]?.textContent || ""],
    ["Source", $("sourceType").selectedOptions[0]?.textContent || ""],
    ["Genre", $("genre").value],
    ["Tag", $("tag").value],
    ["BPM min", $("bpmMin").value],
    ["BPM max", $("bpmMax").value],
    ["Rating", $("rating").selectedOptions[0]?.textContent || ""],
  ].filter(([label, value]) => value && !["All", "All sources", "Any"].includes(value));
  return entries.length ? `Active filters: ${entries.map(([label, value]) => `${label}=${value}`).join(", ")}` : "No filters active";
}

function mediaMatchesPlaylistSearch(item, query) {
  if (!query) return true;
  const haystack = [item.title, item.creator, item.source, item.source_url, item.direct_media_url, item.tags]
    .join(" ")
    .toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function updateQueueCount() {
  $("queueCount").textContent = `Queue: ${state.queue.length}`;
}

function setStatus(id, html) {
  const element = $(id);
  if (element) element.innerHTML = html;
}

function csvSelectionInfo() {
  const input = $("csvFile");
  const file = input.files[0] || null;
  return {
    filesLength: input.files.length,
    name: file?.name || "",
    size: file?.size || 0,
    type: file?.type || "",
  };
}

function showCsvSelection() {
  const info = csvSelectionInfo();
  debugLog("csv:select", info);
  setStatus("csvDebug", `
    <div>input.files.length: ${info.filesLength}</div>
    <div>file: ${escapeHtml(info.name || "-")}</div>
    <div>size: ${info.size}</div>
    <div>MIME type: ${escapeHtml(info.type || "-")}</div>
  `);
}

function showCsvResult(result) {
  setStatus("csvResult", `
    <div>total_rows: ${result.total_rows ?? 0}</div>
    <div>imported: ${result.imported ?? 0}</div>
    <div>duplicates: ${result.duplicates ?? 0}</div>
    <div>playable: ${result.playable ?? 0}</div>
    <div>unplayable: ${result.unplayable ?? 0}</div>
    <div>queued: ${result.queued ?? 0}</div>
    <div>errors: ${result.errors ?? 0}</div>
  `);
}

function summaryLine(label, value) {
  return `<div>${escapeHtml(label)}: ${escapeHtml(value ?? 0)}</div>`;
}

function renderTrackImportPreview(result) {
  state.trackImportToken = result.token || "";
  $("trackImportPanel").classList.remove("hidden");
  $("trackImportState").textContent = "Preview ready";
  $("applyTrackImport").disabled = !state.trackImportToken;
  const fields = result.field_counts || {};
  $("trackImportSummary").innerHTML = [
    summaryLine("CSV rows", result.total_rows),
    summaryLine("Updatable rows", result.updatable_rows),
    summaryLine("Unchanged rows", result.unchanged_rows),
    summaryLine("Error rows", result.error_rows),
    summaryLine("Missing media_id", result.missing_media_id),
    summaryLine("Duplicate media_id", result.duplicate_media_id),
    summaryLine("Not found media_id", result.not_found_media_id),
    summaryLine("Invalid BPM", result.invalid_bpm),
    summaryLine("Invalid rating", result.invalid_rating),
    summaryLine("Empty title", result.empty_title),
    summaryLine("local/R2 sync planned", result.sync_planned),
    `<div>Fields: title ${fields.title || 0}, creator ${fields.creator || 0}, genre ${fields.genre || 0}, bpm ${fields.bpm || 0}, tags ${fields.tags || 0}, rating ${fields.rating || 0}</div>`,
  ].join("");
  $("trackImportExamples").innerHTML = (result.examples || []).length
    ? result.examples.map((item) => `
      <div class="preview-row">
        <strong>${escapeHtml(item.title || "-")}</strong>
        <div>${escapeHtml(item.media_id)} / ${escapeHtml(item.field)}</div>
        <div>${escapeHtml(item.before ?? "")} -> ${escapeHtml(item.after ?? "")}</div>
      </div>
    `).join("")
    : `<div class="status">No changed rows to preview.</div>`;
}

function renderPlaylistImportPreview(result) {
  state.playlistImportToken = result.token || "";
  $("playlistImportPanel").classList.remove("hidden");
  $("playlistImportState").textContent = "Preview ready";
  $("applyPlaylistImport").disabled = !state.playlistImportToken;
  $("playlistImportSummary").innerHTML = [
    summaryLine("Current items", result.current_count),
    summaryLine("After import", result.imported_count),
    summaryLine("Added", result.added_count),
    summaryLine("Removed", result.removed_count),
    summaryLine("Order changes", result.order_changed_count),
    summaryLine("Duplicate media_id", result.duplicate_media_id),
    summaryLine("Missing media_id", result.missing_media_id),
    ...(result.imported_count === 0 ? [`<div class="error">Applying this CSV will empty the playlist.</div>`] : []),
    ...((result.warnings || []).slice(0, 10).map((warning) => `<div>Warning: ${escapeHtml(warning.warning || "")} ${escapeHtml(warning.media_id || "")}</div>`)),
  ].join("");
  $("playlistImportExamples").innerHTML = (result.new_order_preview || []).length
    ? result.new_order_preview.map((item, index) => `
      <div class="preview-row">
        <strong>${index + 1}. ${escapeHtml(item.title || "-")}</strong>
        <div>${escapeHtml(item.media_id)}</div>
      </div>
    `).join("")
    : `<div class="status">The imported playlist will be empty.</div>`;
}

function resetTrackImportPanel(message = "Canceled") {
  state.trackImportToken = "";
  $("trackMetadataCsv").value = "";
  $("applyTrackImport").disabled = true;
  $("trackImportState").textContent = message;
  $("trackImportSummary").innerHTML = "";
  $("trackImportExamples").innerHTML = "";
  $("trackImportPanel").classList.add("hidden");
}

function resetPlaylistImportPanel(message = "Canceled") {
  state.playlistImportToken = "";
  $("playlistCsv").value = "";
  $("applyPlaylistImport").disabled = true;
  $("playlistImportState").textContent = message;
  $("playlistImportSummary").innerHTML = "";
  $("playlistImportExamples").innerHTML = "";
  $("playlistImportPanel").classList.add("hidden");
}

function showScanResult(result) {
  $("scanResult").innerHTML = `
    <div>root: ${escapeHtml(result.root || "-")}</div>
    <div>detected ${result.detected ?? 0} / queued ${result.queued ?? result.added ?? 0} / added ${result.added ?? 0} / duplicates ${result.duplicates ?? 0} / unsupported ${result.unsupported ?? 0} / errors ${result.errors ?? 0}</div>
  `;
  if (typeof result.invalid_media === "number") {
    state.invalidMedia.count = result.invalid_media;
    renderInvalidMedia();
  }
}

function showUrlDiagnosis(result) {
  $("urlDiagnosis").innerHTML = `
    <div>classification: ${escapeHtml(result.classification || "-")}</div>
    <div>final_url: ${escapeHtml(result.final_url || "-")}</div>
    <div>HTTP status: ${escapeHtml(result.http_status ?? "-")}</div>
    <div>Content-Type: ${escapeHtml(result.content_type || "-")}</div>
    <div>Content-Length: ${escapeHtml(result.content_length || "-")}</div>
    <div>Accept-Ranges: ${escapeHtml(result.accept_ranges || "-")}</div>
    <div>Access-Control-Allow-Origin: ${escapeHtml(result.access_control_allow_origin || "-")}</div>
    <div>redirects: ${escapeHtml(result.redirect_count ?? 0)}</div>
    <div>direct media: ${result.is_direct_media ? "yes" : "no"} / playable: ${result.playable ? "yes" : "no"}</div>
    <div>reason: ${escapeHtml(result.unplayable_reason || "-")}</div>
  `;
}

function queueKey(item) {
  return item?.media_id || item?.direct_media_url || item?.source || item?.source_url || "";
}

function uniquePlayableItems(items) {
  const seen = new Set();
  const unique = [];
  let duplicates = 0;
  for (const raw of items || []) {
    const item = normalizeQueueItem(raw);
    if (!isPlayable(item)) continue;
    const key = queueKey(item);
    if (key && seen.has(key)) {
      duplicates += 1;
      continue;
    }
    if (key) seen.add(key);
    unique.push(item);
  }
  return { items: unique, duplicates };
}

function setBulkBusy(isBusy, message = "") {
  state.bulkBusy = isBusy;
  for (const id of ["addFilteredToPlaylist", "createPlaylistFromFiltered", "shuffleFiltered", "replacePlaylistWithFiltered", "deletePlaylist"]) {
    const button = $(id);
    if (button) button.disabled = isBusy || (id === "deletePlaylist" && !state.selectedPlaylist?.playlist_id);
  }
  document.querySelectorAll("[data-action='add-remote-to-playlist'], [data-action='play-remote'], [data-action='shuffle-remote']")
    .forEach((button) => { button.disabled = isBusy; });
  if (message) $("scanResult").textContent = message;
}

function setPlaylistDirty(isDirty, message = "") {
  state.playlistDirty = isDirty;
  const status = $("playlistStatus");
  if (status) status.textContent = message || (isDirty ? "Unsaved changes" : "Saved");
}

function uniqueMediaIds(items) {
  const seen = new Set();
  const ids = [];
  for (const item of items || []) {
    if (item.media_id && !seen.has(item.media_id)) {
      seen.add(item.media_id);
      ids.push(item.media_id);
    }
  }
  return ids;
}

function shuffled(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function sourceFor(item) {
  if (item.play_url) return item.play_url;
  if (item.direct_media_url) return item.direct_media_url;
  if (item.source_type === "suno") return "";
  if (item.source_type === "local") return `/media/${encodeURIComponent(item.media_id)}`;
  if (item.source_type === "local_path") return `/local-media?source=${encodeURIComponent(item.source)}`;
  return item.source;
}

function isPlayable(item) {
  if (!item) return false;
  if (item.playable === false) return false;
  if (item.direct_media_url) return true;
  if (item.source_type === "suno") return false;
  return Boolean(sourceFor(item));
}

function normalizeQueueItem(item) {
  const playUrl = item.play_url || item.direct_media_url || (
    item.source_type === "suno" ? "" : sourceFor(item)
  );
  return {
    ...item,
    source_url: item.source_url || "",
    direct_media_url: item.direct_media_url || "",
    play_url: playUrl,
    playable: Boolean(playUrl),
  };
}

function showPlaybackError(item, player, err) {
  const mediaError = player?.error;
  const code = mediaError?.code ?? "";
  const playUrl = item?.play_url || sourceFor(item);
  const message = err?.message || mediaError?.message || "Playback failed";
  debugLog("play:item:error", {
    title: item?.title,
    code,
    message,
    play_url: playUrl,
    mediaError,
  });
  $("scanResult").textContent = `Playback failed: code ${code || "-"} / ${message} / ${playUrl}`;
}

function activeElement() {
  return state.current?.media_type === "video" ? video : audio;
}

function bpmText(item) {
  if (item?.bpm) return `${item.bpm} BPM`;
  if (item?.bpm_analysis_status === "running") return "BPM: analyzing...";
  if (item?.bpm_analysis_status === "failed") return "BPM: analysis failed";
  return "no BPM";
}

function updateNowBpm() {
  $("nowBpm").textContent = state.current ? bpmText(state.current) : "BPM: -";
}

function sameTrack(a, b) {
  if (!a || !b) return false;
  if (a.media_id && b.media_id && a.media_id === b.media_id) return true;
  return queueKey(a) === queueKey(b);
}

function mergeBpmState(target, patch) {
  if (!target || !patch) return;
  for (const key of ["bpm", "bpm_analysis_status", "bpm_analyzed_at", "bpm_method"]) {
    if (Object.prototype.hasOwnProperty.call(patch, key)) target[key] = patch[key] ?? "";
  }
}

function applyBpmStateToClient(originalItem, patch) {
  for (const item of state.media) {
    if (sameTrack(item, originalItem) || item.media_id === patch.media_id) mergeBpmState(item, patch);
  }
  for (const item of state.queue) {
    if (sameTrack(item, originalItem) || item.media_id === patch.media_id) mergeBpmState(item, patch);
  }
  for (const playlist of state.playlists) {
    for (const item of playlist.items || []) {
      if (sameTrack(item, originalItem) || item.media_id === patch.media_id) mergeBpmState(item, patch);
    }
  }
  if (state.current && (sameTrack(state.current, originalItem) || state.current.media_id === patch.media_id)) {
    mergeBpmState(state.current, patch);
    updateNowBpm();
  }
  renderMedia();
  renderPlaylists();
}

function clearBpmTimers() {
  if (state.bpmAnalyzeTimer) {
    clearTimeout(state.bpmAnalyzeTimer);
    state.bpmAnalyzeTimer = null;
  }
  if (state.bpmPollTimer) {
    clearTimeout(state.bpmPollTimer);
    state.bpmPollTimer = null;
  }
}

function pollBpmAnalysis(analysisId, originalItem) {
  if (!analysisId) return;
  state.bpmPollTimer = setTimeout(async () => {
    try {
      const result = await api(`/api/media/${encodeURIComponent(analysisId)}/bpm-analysis`);
      const patch = result.item || result;
      applyBpmStateToClient(originalItem, patch);
      if (result.bpm_analysis_status === "running") {
        pollBpmAnalysis(analysisId, originalItem);
      } else {
        await loadMedia(true);
        await loadPlaylists();
      }
    } catch (err) {
      console.error("Failed to poll BPM analysis", err);
    }
  }, 3000);
}

async function requestBpmAnalysis(originalItem) {
  if (!originalItem || originalItem.bpm || ["running", "failed"].includes(originalItem.bpm_analysis_status)) return;
  const analyzingPatch = {
    media_id: originalItem.media_id,
    bpm: "",
    bpm_analysis_status: "running",
    bpm_analyzed_at: "",
    bpm_method: "",
  };
  applyBpmStateToClient(originalItem, analyzingPatch);
  try {
    const result = await api(`/api/media/${encodeURIComponent(originalItem.media_id || "queue")}/bpm-analysis`, {
      method: "POST",
      body: JSON.stringify(originalItem),
    });
    const patch = result.item || analyzingPatch;
    if (result.status === "done" && result.bpm) patch.bpm = result.bpm;
    if (result.status) patch.bpm_analysis_status = result.status;
    applyBpmStateToClient(originalItem, patch);
    const analysisId = result.media_ids?.[0] || patch.media_id || originalItem.media_id;
    if (result.status === "running") pollBpmAnalysis(analysisId, originalItem);
    if (result.status === "done") {
      await loadMedia(true);
      await loadPlaylists();
    }
  } catch (err) {
    console.error("Failed to enqueue BPM analysis", err);
    applyBpmStateToClient(originalItem, {
      media_id: originalItem.media_id,
      bpm_analysis_status: "failed",
    });
  }
}

function scheduleBpmAnalysis(item) {
  if (!item || item.media_type !== "audio" || item.bpm || ["running", "failed"].includes(item.bpm_analysis_status)) return;
  if (state.bpmAnalyzeTimer) clearTimeout(state.bpmAnalyzeTimer);
  const queuedItem = { ...item };
  state.bpmAnalyzeTimer = setTimeout(() => {
    state.bpmAnalyzeTimer = null;
    if (!state.current || !sameTrack(state.current, queuedItem)) return;
    requestBpmAnalysis(queuedItem);
  }, 5000);
}

function setQueue(items, { shuffle = false, autoplay = true } = {}) {
  debugLog("queue:set:start", { incoming: items?.length || 0, shuffle, autoplay });
  const result = uniquePlayableItems(items);
  state.queue = shuffle ? shuffled(result.items) : [...result.items];
  state.queue.forEach((item) => delete item.failed);
  state.currentIndex = -1;
  updateQueueCount();
  debugLog("queue:set:done", { queueLength: state.queue.length, skippedDuplicates: result.duplicates, first: state.queue[0]?.play_url });
  if (result.duplicates) $("scanResult").textContent = `Queued: ${state.queue.length} / Skipped duplicates: ${result.duplicates}`;
  if (autoplay && state.queue.length) playItem(state.queue[0], state.queue);
  return { queued: state.queue.length, duplicates: result.duplicates };
}

function selectFirstPlayable(items) {
  const first = items.find(isPlayable);
  if (!first) return;
  state.current = first;
  state.currentIndex = state.queue.findIndex((item) => item.media_id === first.media_id);
  $("nowType").textContent = first.media_type;
  $("nowTitle").textContent = first.title;
  $("nowMeta").textContent = first.source_url || first.source;
  updateNowBpm();
  $("playPause").textContent = "Play";
  renderMedia();
}

async function playItem(item, queue = state.queue) {
  item = normalizeQueueItem(item);
  if (!isPlayable(item)) {
    item.failed = true;
    debugLog("play:item:skip-unplayable", { title: item?.title, sourceUrl: item?.source_url, play_url: item?.play_url });
    playNext(1, true);
    return;
  }
  debugLog("play:item:start", { title: item?.title, play_url: item?.play_url, sourceUrl: item?.source_url, queueLength: queue.length });
  if (state.bpmAnalyzeTimer) {
    clearTimeout(state.bpmAnalyzeTimer);
    state.bpmAnalyzeTimer = null;
  }
  state.current = item;
  state.queue = uniquePlayableItems(queue.length ? queue : [item]).items;
  state.currentIndex = state.queue.findIndex((entry) => entry.media_id === item.media_id);
  updateQueueCount();

  const player = item.media_type === "video" ? video : audio;
  const other = item.media_type === "video" ? audio : video;
  other.pause();
  other.removeAttribute("src");
  other.load();
  video.style.display = item.media_type === "video" ? "block" : "none";
  player.src = item.play_url;
  player.volume = Number($("volume").value);
  player.load();
  $("nowType").textContent = item.media_type;
  $("nowTitle").textContent = item.title;
  $("nowMeta").textContent = item.play_url;
  updateNowBpm();
  $("playPause").textContent = "Pause";
  renderMedia();

  try {
    await player.play();
    debugLog("play:item:playing", { title: item.title });
    scheduleBpmAnalysis(item);
    if (item.source_type === "local") {
      api(`/api/media/${encodeURIComponent(item.media_id)}/played`, { method: "POST", body: "{}" }).then(() => loadMedia(true));
    }
  } catch (err) {
    showPlaybackError(item, player, err);
    if (err.name === "NotAllowedError") {
      console.warn("Playback blocked by browser policy; queue is preserved", item.source, err);
      $("playPause").textContent = "Play";
      return;
    }
    console.warn("Playback failed, skipping", item.source, err);
    item.failed = true;
    playNext(1, true);
  }
}

function nextIndex(direction = 1, ignoreRepeatOne = false) {
  if (!state.queue.length) return -1;
  if (state.repeat === "one" && !ignoreRepeatOne) return state.currentIndex;
  let index = state.currentIndex;
  for (let step = 0; step < state.queue.length; step += 1) {
    index += direction;
    if (index >= 0 && index < state.queue.length) {
      if (!state.queue[index].failed && isPlayable(state.queue[index])) return index;
      continue;
    }
    if (state.repeat === "all") {
      index = direction > 0 ? 0 : state.queue.length - 1;
      if (!state.queue[index].failed && isPlayable(state.queue[index])) return index;
      continue;
    }
    return -1;
  }
  return -1;
}

function playNext(direction = 1, ignoreRepeatOne = false) {
  const index = nextIndex(direction, ignoreRepeatOne);
  if (index === -1) {
    $("playPause").textContent = "Play";
    return;
  }
  playItem(state.queue[index], state.queue);
}

async function loadMedia(preserveQueue = false) {
  const requestSeq = ++state.mediaRequestSeq;
  state.mediaLoading = true;
  state.mediaError = "";
  renderMedia();
  const params = filtersQuery();
  params.set("page", state.mediaPage);
  params.set("page_size", state.mediaPageSize);
  const path = `/api/media?${params.toString()}`;
  try {
    debugLog("filters:load", { path, filters: Object.fromEntries(filtersQuery()) });
    const result = await api(path);
    if (requestSeq !== state.mediaRequestSeq) {
      debugLog("filters:stale-response", { path, requestSeq, latest: state.mediaRequestSeq });
      return;
    }
    state.media = itemsFromResponse(result);
    state.mediaPage = result.page || state.mediaPage;
    state.mediaPageSize = result.page_size || state.mediaPageSize;
    state.mediaTotal = result.total ?? state.media.length;
    state.mediaTotalAll = result.total_all ?? state.mediaTotal;
    state.mediaTotalPages = result.total_pages || 1;
    if (!preserveQueue && !state.queue.length) updateQueueCount();
    const exportParams = filtersQuery();
    $("exportCsv").href = `/api/export/media.csv?${exportParams.toString()}`;
    $("exportViewCsv").href = `/api/media/export.csv?${exportParams.toString()}`;
  } catch (err) {
    if (requestSeq !== state.mediaRequestSeq) return;
    state.media = [];
    state.mediaError = err.message;
    console.error("Failed to load tracks", err);
  } finally {
    if (requestSeq === state.mediaRequestSeq) {
      state.mediaLoading = false;
      renderMedia();
      renderPlaylists();
    }
  }
}

function currentTrackExportUrl() {
  const exportParams = filtersQuery();
  const query = exportParams.toString();
  return `/api/media/export.csv${query ? `?${query}` : ""}`;
}

function legacyTrackExportUrl() {
  const exportParams = filtersQuery();
  const query = exportParams.toString();
  return `/api/export/media.csv${query ? `?${query}` : ""}`;
}

async function loadAllFilteredMedia() {
  const params = filtersQuery();
  return itemsFromResponse(await api(`/api/media?${params.toString()}`));
}

async function loadFolders() {
  state.folders = await api("/api/folders");
  renderFolders();
}

async function loadRemoteLibraries() {
  state.remoteLibraries = await api("/api/remote-libraries");
  renderFolders();
}

async function loadInvalidMedia() {
  state.invalidMedia = await api("/api/invalid-media");
  renderInvalidMedia();
}

async function loadPlaylists() {
  state.playlists = await api("/api/playlists");
  if (state.selectedPlaylist) {
    const found = state.playlists.find((p) => p.playlist_id === state.selectedPlaylist.playlist_id);
    if (found) {
      state.selectedPlaylist = found;
      state.playlistDraft = found.items.map((item) => item.media_id);
    } else {
      state.selectedPlaylist = state.playlists[0] || null;
      state.playlistDraft = state.selectedPlaylist?.items.map((item) => item.media_id) || [];
    }
  } else if (state.playlists.length) {
    state.selectedPlaylist = state.playlists[0];
    state.playlistDraft = state.selectedPlaylist.items.map((item) => item.media_id);
  }
  renderPlaylists();
}

function renderInvalidMedia() {
  const count = state.invalidMedia.count || 0;
  if (!count) {
    $("invalidMedia").textContent = "Invalid folder media: 0";
    $("deleteInvalid").classList.add("hidden");
    return;
  }
  const first = state.invalidMedia.items?.[0]?.source || "";
  $("invalidMedia").textContent = `Invalid folder media: ${count}. ${first}`;
  $("deleteInvalid").classList.remove("hidden");
}

function folderCard(folder) {
  const normalized = String(folder.path || "").replace(/[\\/]+$/, "");
  const folderName = normalized.split(/[\\/]/).pop() || normalized || "Folder";
  return `
    <div class="folder-row" data-folder="${folder.folder_id}">
      <div class="folder-info">
        <strong class="folder-name" title="${escapeHtml(folderName)}">${escapeHtml(folderName)}</strong>
        <small class="folder-path" title="${escapeHtml(folder.path)}">${escapeHtml(folder.path)}</small>
      </div>
      <div class="folder-actions">
        <button data-action="play-folder">Play</button>
        <button data-action="shuffle-folder">Shuffle</button>
        <button data-action="rescan">Rescan</button>
        <button data-action="remove-folder">Remove</button>
      </div>
    </div>
  `;
}

function remoteLibraryCard(library) {
  return `
    <div class="folder-row remote-row" data-remote-key="${escapeHtml(library.key)}">
      <div class="folder-info">
        <strong class="folder-name" title="${escapeHtml(library.name)}">${escapeHtml(library.name)}</strong>
        <small class="folder-path" title="source_type=${escapeHtml(library.source_type)} tag=${escapeHtml(library.tag)}">${library.count} tracks</small>
      </div>
      <div class="folder-actions">
        <button data-action="play-remote">Play</button>
        <button data-action="shuffle-remote">Shuffle</button>
        <button data-action="view-remote">View tracks</button>
        <button data-action="add-remote-to-playlist">Add to playlist</button>
      </div>
    </div>
  `;
}

function renderFolders() {
  const localHtml = state.folders.length
    ? state.folders.map(folderCard).join("")
    : `<div class="status">No registered folders yet.</div>`;
  const remoteHtml = state.remoteLibraries.length
    ? state.remoteLibraries.map(remoteLibraryCard).join("")
    : `<div class="status">No remote libraries yet.</div>`;
  const html = `<h3>Local folders</h3>${localHtml}<h3>Remote libraries</h3>${remoteHtml}`;
  $("folderList").innerHTML = html;
  $("folderCards").innerHTML = html;
}

function itemHtml(item, compact = false) {
  const active = state.current?.media_id === item.media_id ? " active" : "";
  const bpm = bpmText(item);
  const rating = "*".repeat(Number(item.rating || 0)) || "no rating";
  const playable = isPlayable(item);
  const sourceLabel = item.source_type === "suno" ? "suno" : item.source_type;
  const sourceLine = item.source_type === "suno"
    ? `${item.source_url || "no source page"}${item.direct_media_url ? " / playable" : " / no direct media URL"}`
    : item.source;
  return `
    <div class="item${active}" data-id="${item.media_id}">
      <div>
        <div class="item-title">${escapeHtml(item.title)}</div>
        <div class="meta">${escapeHtml(item.creator || "unknown creator")} / ${escapeHtml(sourceLabel)} / ${escapeHtml(item.media_type)} / ${escapeHtml(item.tags || "no tags")} / ${escapeHtml(bpm)}</div>
        ${compact ? "" : `<div class="meta">${escapeHtml(sourceLine)} / plays ${item.play_count || 0} / ${rating}</div>`}
      </div>
      <div class="actions">
        <button data-action="play" ${playable ? "" : "disabled"}>Play</button>
        ${item.source_url ? `<button data-action="open-source">Open</button>` : ""}
        ${compact ? `<button data-action="remove-from-playlist">Remove</button>` : `<button data-action="add-to-playlist">Add</button><button data-action="delete">Del</button>`}
      </div>
    </div>
  `;
}

function renderMedia() {
  if (state.mediaLoading) {
    $("trackStats").textContent = `Filtering... ${activeFilterSummary()}`;
  } else if (state.mediaError) {
    $("trackStats").textContent = `Failed to load tracks: ${state.mediaError}`;
  } else if (state.mediaTotal === 0) {
    $("trackStats").textContent = `No tracks match the current filters. ${activeFilterSummary()}`;
  } else {
    const countText = state.mediaTotal === state.mediaTotalAll
      ? `${showingLabel(state.mediaPage, state.mediaPageSize, state.mediaTotal)} tracks`
      : `Filtered: ${state.mediaTotal} of ${state.mediaTotalAll} tracks. ${showingLabel(state.mediaPage, state.mediaPageSize, state.mediaTotal)}`;
    $("trackStats").textContent = `${countText}. ${activeFilterSummary()}`;
  }
  $("trackPageLabel").textContent = pageLabel(state.mediaPage, state.mediaTotalPages);
  $("trackPrev").disabled = state.mediaPage <= 1;
  $("trackNext").disabled = state.mediaPage >= state.mediaTotalPages;
  $("trackPageSize").value = String(state.mediaPageSize);
  if (state.mediaLoading) {
    $("mediaList").innerHTML = `<div class="item"><div><div class="item-title">Filtering...</div><div class="meta">Loading tracks for the current filters.</div></div></div>`;
    return;
  }
  if (state.mediaError) {
    $("mediaList").innerHTML = `<div class="item"><div><div class="item-title">Failed to load tracks</div><div class="meta">${escapeHtml(state.mediaError)}</div></div></div>`;
    return;
  }
  $("mediaList").innerHTML = state.media.length
    ? state.media.map((item) => itemHtml(item)).join("")
    : `<div class="item"><div><div class="item-title">No tracks match the current filters.</div><div class="meta">Clear filters or adjust the values above.</div></div></div>`;
}

function setView(view) {
  state.view = view;
  $("folderCards").classList.toggle("hidden", view !== "folders");
  $("mediaList").classList.toggle("hidden", view !== "tracks");
  $("showFolders").classList.toggle("primary", view === "folders");
  $("showTracks").classList.toggle("primary", view === "tracks");
}

function renderPlaylists() {
  $("playlistList").innerHTML = state.playlists.map((playlist) => `
    <button class="playlist-button${state.selectedPlaylist?.playlist_id === playlist.playlist_id ? " active" : ""}" data-playlist="${playlist.playlist_id}">
      <strong>${escapeHtml(playlist.name)}</strong>
      <small>${playlist.items.length} items</small>
    </button>
  `).join("");
  const allItems = state.playlistDraft
    .map((id) => state.media.find((item) => item.media_id === id) || state.selectedPlaylist?.items.find((item) => item.media_id === id))
    .filter(Boolean);
  const playlistQuery = $("playlistSearch")?.value.trim() || "";
  const filteredItems = allItems.filter((item) => mediaMatchesPlaylistSearch(item, playlistQuery));
  state.playlistFilteredTotal = filteredItems.length;
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / state.playlistPageSize));
  state.playlistPage = Math.min(Math.max(1, state.playlistPage), totalPages);
  const start = (state.playlistPage - 1) * state.playlistPageSize;
  const pageItems = filteredItems.slice(start, start + state.playlistPageSize);
  $("playlistItems").innerHTML = pageItems.length
    ? pageItems.map((item) => itemHtml(item, true)).join("")
    : `<div class="item"><div><div class="item-title">No playlist tracks</div><div class="meta">Add tracks or adjust playlist search.</div></div></div>`;
  $("playlistName").value = state.selectedPlaylist?.name || "";
  const selectedName = state.selectedPlaylist?.name || "No playlist";
  const totalItems = allItems.length;
  $("playlistStats").textContent = state.selectedPlaylist
    ? `${selectedName}: ${totalItems} items. ${filteredItems.length === totalItems ? showingLabel(state.playlistPage, state.playlistPageSize, filteredItems.length) : `Filtered: ${filteredItems.length} of ${totalItems}. ${showingLabel(state.playlistPage, state.playlistPageSize, filteredItems.length)}`}`
    : "No playlist selected";
  $("playlistPageLabel").textContent = pageLabel(state.playlistPage, totalPages);
  $("playlistPrev").disabled = state.playlistPage <= 1;
  $("playlistNext").disabled = state.playlistPage >= totalPages;
  if (state.selectedPlaylist?.playlist_id) {
    $("exportPlaylist").href = `/api/playlists/${encodeURIComponent(state.selectedPlaylist.playlist_id)}/export.csv`;
    $("exportPlaylist").classList.remove("disabled");
    $("deletePlaylist").disabled = false;
  } else {
    $("exportPlaylist").removeAttribute("href");
    $("exportPlaylist").classList.add("disabled");
    $("deletePlaylist").disabled = true;
  }
  setPlaylistDirty(state.playlistDirty);
}

async function openFolder({ shuffle = false } = {}) {
  const source = $("folderPath").value.trim();
  if (!source) return alert("Enter a folder path.");
  debugLog("openFolder:click", { source, shuffle });
  const result = await api("/api/folders/open", {
    method: "POST",
    body: JSON.stringify({ source }),
  });
  debugLog("openFolder:result", { detected: result.detected, queued: result.queued, itemsLength: result.items?.length || 0 });
  showScanResult(result);
  setQueue(result.items, { shuffle, autoplay: true });
}

$("openFolder").addEventListener("click", () => openFolder());
$("openFile").addEventListener("click", async () => {
  const source = $("filePath").value.trim();
  if (!source) return alert("Enter a file path.");
  const result = await api("/api/files/open", {
    method: "POST",
    body: JSON.stringify({ source }),
  });
  showScanResult(result);
  setQueue(result.items, { autoplay: true });
});

$("openUrl").addEventListener("click", async () => {
  const source = $("urlSource").value.trim();
  if (!source) return alert("Enter a URL.");
  const diagnosis = await api("/api/diagnose-url", {
    method: "POST",
    body: JSON.stringify({ url: source }),
  });
  debugLog("url:diagnosis", diagnosis);
  showUrlDiagnosis(diagnosis);
  if (diagnosis.classification !== "direct_media" || !diagnosis.playable) {
    $("scanResult").textContent = `URL not queued: ${diagnosis.unplayable_reason || diagnosis.classification}`;
    return;
  }
  const item = {
    media_id: `url-${Date.now()}`,
    title: diagnosis.final_url.split("/").pop() || diagnosis.final_url,
    creator: "",
    media_type: diagnosis.media_type || $("urlMediaType").value,
    source_type: "url",
    source: diagnosis.final_url,
    source_url: "",
    direct_media_url: diagnosis.final_url,
    play_url: diagnosis.final_url,
    playable: true,
    genre: "",
    bpm: "",
    tags: "",
    rating: 0,
    play_count: 0,
  };
  setQueue([item], { autoplay: true });
  $("scanResult").textContent = "URL queued: 1";
});

$("addFolderLibrary").addEventListener("click", async () => {
  const source = $("folderPath").value.trim();
  if (!source) return alert("Enter a folder path.");
  debugLog("addFolderLibrary:click", { source });
  const result = await api("/api/folders/scan", {
    method: "POST",
    body: JSON.stringify({ source, source_type: "local" }),
  });
  showScanResult(result);
  await loadMedia();
  await loadFolders();
  await loadInvalidMedia();
});

function remoteQuery(library) {
  const params = new URLSearchParams();
  params.set("remote_library", library.key);
  return params;
}

async function loadRemoteTracks(library) {
  return api(`/api/media?${remoteQuery(library).toString()}`);
}

async function createPlaylist(name) {
  const trimmed = String(name || "").trim();
  if (!trimmed) throw new Error("Playlist name is required.");
  if (state.playlists.some((playlist) => playlist.name.toLowerCase() === trimmed.toLowerCase())) {
    throw new Error(`Playlist "${trimmed}" already exists.`);
  }
  const result = await api("/api/playlists", {
    method: "POST",
    body: JSON.stringify({ name: trimmed, media_ids: [] }),
  });
  state.selectedPlaylist = { playlist_id: result.playlist_id, name: trimmed, items: [] };
  await loadPlaylists();
  setPlaylistDirty(false, "Saved");
  return state.selectedPlaylist || result;
}

function playlistNameInputValue() {
  return $("playlistName").value.trim();
}

function requirePlaylistName(actionLabel) {
  const name = playlistNameInputValue();
  if (name) return name;
  $("playlistName").focus();
  throw new Error(`Enter a playlist name before ${actionLabel}.`);
}

function confirmAction(message, { okLabel = "OK" } = {}) {
  return new Promise((resolve) => {
    const existing = document.querySelector(".confirm-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.className = "confirm-overlay";
    overlay.innerHTML = `
      <div class="confirm-panel" role="dialog" aria-modal="true">
        <div class="confirm-message"></div>
        <div class="confirm-actions">
          <button type="button" data-confirm="cancel">Cancel</button>
          <button type="button" class="primary" data-confirm="ok"></button>
        </div>
      </div>
    `;
    overlay.querySelector(".confirm-message").textContent = message;
    overlay.querySelector("[data-confirm='ok']").textContent = okLabel;
    document.body.appendChild(overlay);

    const finish = (value) => {
      overlay.remove();
      resolve(value);
    };
    overlay.querySelector("[data-confirm='cancel']").addEventListener("click", () => finish(false));
    overlay.querySelector("[data-confirm='ok']").addEventListener("click", () => finish(true));
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) finish(false);
    });
    overlay.querySelector("[data-confirm='ok']").focus();
  });
}

async function bulkAddItemsToPlaylist(items, label) {
  if (!state.selectedPlaylist?.playlist_id) {
    alert("Select a playlist first.");
    return null;
  }
  const playlistId = state.selectedPlaylist.playlist_id;
  const playlistName = state.selectedPlaylist.name;
  const ids = uniqueMediaIds(items);
  if (!ids.length) {
    alert("No tracks to add.");
    return null;
  }
  if (!(await confirmAction(`Add ${ids.length} filtered tracks to "${playlistName}"?`))) return null;
  setBulkBusy(true, `Adding ${ids.length} tracks...`);
  try {
    const result = await api(`/api/playlists/${encodeURIComponent(playlistId)}/items/bulk`, {
      method: "POST",
      body: JSON.stringify({ media_ids: ids }),
    });
    state.selectedPlaylist = { playlist_id: playlistId, name: playlistName, items: [] };
    await loadPlaylists();
    const refreshed = state.playlists.find((playlist) => playlist.playlist_id === playlistId);
    if (refreshed) {
      state.selectedPlaylist = refreshed;
      state.playlistDraft = refreshed.items.map((item) => item.media_id);
    }
    setPlaylistDirty(false, "Saved");
    renderPlaylists();
    $("scanResult").textContent = `Added: ${result.added} / Skipped duplicates: ${result.duplicates} / Errors: ${result.errors}`;
    return result;
  } catch (err) {
    $("scanResult").textContent = `Failed to add tracks: ${err.message}`;
    console.error("Failed to add tracks", err);
    return null;
  } finally {
    setBulkBusy(false);
  }
}

async function handleRemoteAction(row, action) {
  const library = state.remoteLibraries.find((entry) => entry.key === row.dataset.remoteKey);
  if (!library) return;
  if (action === "view-remote") {
    state.activeRemoteLibrary = library.key;
    $("sourceType").value = library.source_type;
    $("tag").value = library.tag;
    setView("tracks");
    await loadMedia();
    return;
  }
  const items = await loadRemoteTracks(library);
  if (action === "play-remote" || action === "shuffle-remote") {
    const result = setQueue(items, { shuffle: action === "shuffle-remote", autoplay: true });
    $("scanResult").textContent = `Queued: ${result.queued} / Skipped duplicates: ${result.duplicates}`;
  }
  if (action === "add-remote-to-playlist") await bulkAddItemsToPlaylist(items, library.name);
}

async function handleFolderAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const remoteRow = event.target.closest("[data-remote-key]");
  if (remoteRow) return handleRemoteAction(remoteRow, button.dataset.action);
  const row = event.target.closest("[data-folder]");
  if (!row) return;
  const id = row.dataset.folder;
  const action = button.dataset.action;
  if (action === "play-folder" || action === "shuffle-folder") {
    const result = await api(`/api/folders/${encodeURIComponent(id)}/play`, {
      method: "POST",
      body: JSON.stringify({ shuffle: action === "shuffle-folder" }),
    });
    showScanResult(result);
    setQueue(result.items, { autoplay: true });
  }
  if (action === "rescan") {
    const result = await api(`/api/folders/${encodeURIComponent(id)}/rescan`, { method: "POST", body: "{}" });
    showScanResult(result);
    await loadMedia();
    await loadFolders();
    await loadInvalidMedia();
  }
  if (action === "remove-folder" && confirm("Remove this folder from registered folders?")) {
    await fetch(`/api/folders/${encodeURIComponent(id)}`, { method: "DELETE" });
    await loadFolders();
  }
}

$("folderList").addEventListener("click", handleFolderAction);
$("folderCards").addEventListener("click", handleFolderAction);

$("deleteInvalid").addEventListener("click", async () => {
  const count = state.invalidMedia.count || 0;
  if (!count) return;
  if (!confirm(`Delete ${count} invalid folder media record(s)?`)) return;
  const result = await api("/api/invalid-media/delete", { method: "POST", body: "{}" });
  $("scanResult").textContent = `Deleted ${result.deleted} invalid folder media record(s).`;
  await loadMedia();
  await loadInvalidMedia();
});

function applyTrackFilters() {
  if (state.filterTimer) {
    clearTimeout(state.filterTimer);
    state.filterTimer = null;
  }
  state.activeRemoteLibrary = "";
  state.mediaPage = 1;
  loadMedia();
}

function handleTrackFilterChange(event) {
  const immediate = event.type === "change" || event.key === "Enter" || event.target.tagName === "SELECT";
  if (state.filterTimer) clearTimeout(state.filterTimer);
  if (immediate) {
    applyTrackFilters();
    return;
  }
  state.filterTimer = setTimeout(applyTrackFilters, 300);
}

for (const id of ["q", "mediaType", "sourceType", "genre", "tag", "bpmMin", "bpmMax", "rating"]) {
  const field = $(id);
  if (field.tagName === "SELECT") {
    field.addEventListener("change", handleTrackFilterChange);
  } else {
    field.addEventListener("input", handleTrackFilterChange);
    field.addEventListener("change", handleTrackFilterChange);
  }
  field.addEventListener("keydown", (event) => {
    if (event.key === "Enter") handleTrackFilterChange(event);
  });
}

$("clearFilters").addEventListener("click", () => {
  for (const id of ["q", "mediaType", "sourceType", "genre", "tag", "bpmMin", "bpmMax", "rating"]) {
    $(id).value = "";
  }
  state.activeRemoteLibrary = "";
  state.mediaPage = 1;
  loadMedia();
});


$("trackPrev").addEventListener("click", () => {
  if (state.mediaPage <= 1) return;
  state.mediaPage -= 1;
  loadMedia(true);
});

$("trackNext").addEventListener("click", () => {
  if (state.mediaPage >= state.mediaTotalPages) return;
  state.mediaPage += 1;
  loadMedia(true);
});

$("trackPageSize").addEventListener("change", () => {
  state.mediaPageSize = Number($("trackPageSize").value || 50);
  state.mediaPage = 1;
  loadMedia(true);
});

$("playlistSearch").addEventListener("input", () => {
  state.playlistPage = 1;
  renderPlaylists();
});

$("playlistPrev").addEventListener("click", () => {
  if (state.playlistPage <= 1) return;
  state.playlistPage -= 1;
  renderPlaylists();
});

$("playlistNext").addEventListener("click", () => {
  state.playlistPage += 1;
  renderPlaylists();
});

$("showFolders").addEventListener("click", () => setView("folders"));
$("showTracks").addEventListener("click", () => setView("tracks"));

$("mediaList").addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  const row = event.target.closest(".item");
  if (!button || !row) return;
  const item = state.media.find((entry) => entry.media_id === row.dataset.id);
  if (!item) return;
  if (button.dataset.action === "play") setQueue(state.media, { autoplay: false }), playItem(item, state.media);
  if (button.dataset.action === "open-source" && item.source_url) window.open(item.source_url, "_blank", "noopener");
  if (button.dataset.action === "delete" && confirm("Delete this media item?")) {
    await fetch(`/api/media/${encodeURIComponent(item.media_id)}`, { method: "DELETE" });
    await loadMedia();
    await loadPlaylists();
    await loadInvalidMedia();
  }
  if (button.dataset.action === "add-to-playlist") {
    if (!state.selectedPlaylist) {
      state.selectedPlaylist = { playlist_id: null, name: "New playlist", items: [] };
      state.playlistDraft = [];
    }
    if (!state.playlistDraft.includes(item.media_id)) {
      state.playlistDraft.push(item.media_id);
      setPlaylistDirty(true);
    }
    renderPlaylists();
  }
});

$("shuffleFiltered").addEventListener("click", async () => {
  setBulkBusy(true, "Loading all filtered tracks...");
  try {
    const items = await loadAllFilteredMedia();
    setQueue(items, { shuffle: true, autoplay: true });
    $("scanResult").textContent = `Queued: ${state.queue.length} filtered tracks.`;
  } catch (err) {
    $("scanResult").textContent = `Failed to shuffle filtered tracks: ${err.message}`;
    console.error("Failed to shuffle filtered tracks", err);
  } finally {
    setBulkBusy(false);
  }
});

function handlePlaylistItemClick(event) {
  if (event.__playlistHandled) return;
  const button = event.target.closest("button");
  const row = event.target.closest(".item");
  if (!button || !row) return;
  if (!row.closest("#playlistItems")) return;
  event.__playlistHandled = true;
  const item = state.media.find((entry) => entry.media_id === row.dataset.id) || state.selectedPlaylist?.items.find((entry) => entry.media_id === row.dataset.id);
  if (button.dataset.action === "play" && item) {
    const queue = state.playlistDraft.map((id) => state.media.find((entry) => entry.media_id === id)).filter(Boolean);
    setQueue(queue, { autoplay: false });
    playItem(item, queue);
  }
  if (button.dataset.action === "open-source" && item?.source_url) window.open(item.source_url, "_blank", "noopener");
  if (button.dataset.action === "remove-from-playlist") {
    debugLog("playlist:remove:click", { media_id: row.dataset.id, before: state.playlistDraft.length });
    state.playlistDraft = state.playlistDraft.filter((id) => id !== row.dataset.id);
    setPlaylistDirty(true);
    renderPlaylists();
    debugLog("playlist:remove:done", { after: state.playlistDraft.length });
  }
}

$("playlistItems").addEventListener("click", handlePlaylistItemClick);
document.addEventListener("click", handlePlaylistItemClick);

$("playlistList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-playlist]");
  if (!button) return;
  state.selectedPlaylist = state.playlists.find((p) => p.playlist_id === button.dataset.playlist);
  state.playlistDraft = state.selectedPlaylist.items.map((item) => item.media_id);
  state.playlistPage = 1;
  $("playlistSearch").value = "";
  setPlaylistDirty(false);
  renderPlaylists();
});

$("newPlaylist").addEventListener("click", async () => {
  setBulkBusy(true, "Creating playlist...");
  try {
    const name = requirePlaylistName("creating a playlist");
    const playlist = await createPlaylist(name);
    $("scanResult").textContent = `Created empty playlist "${playlist.name}".`;
  } catch (err) {
    $("scanResult").textContent = `Failed to create playlist: ${err.message}`;
    console.error("Failed to create playlist", err);
  } finally {
    setBulkBusy(false);
  }
});

$("savePlaylist").addEventListener("click", async () => {
  const payload = {
    playlist_id: state.selectedPlaylist?.playlist_id,
    name: $("playlistName").value || "New playlist",
    media_ids: state.playlistDraft,
  };
  setBulkBusy(true, "Saving playlist...");
  try {
    const result = await api(payload.playlist_id ? `/api/playlists/${encodeURIComponent(payload.playlist_id)}` : "/api/playlists", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedPlaylist = { playlist_id: result.playlist_id || payload.playlist_id, name: payload.name, items: [] };
    await loadPlaylists();
    const refreshed = state.playlists.find((playlist) => playlist.playlist_id === state.selectedPlaylist.playlist_id);
    if (refreshed) {
      state.selectedPlaylist = refreshed;
      state.playlistDraft = refreshed.items.map((item) => item.media_id);
    }
    setPlaylistDirty(false, "Saved");
    $("scanResult").textContent = `Saved playlist "${payload.name}".`;
  } catch (err) {
    $("scanResult").textContent = `Failed to save playlist: ${err.message}`;
    console.error("Failed to save playlist", err);
  } finally {
    setBulkBusy(false);
  }
});

$("deletePlaylist").addEventListener("click", async () => {
  const playlist = state.selectedPlaylist;
  if (!playlist?.playlist_id) return;
  const confirmed = await confirmAction(
    `Delete playlist "${playlist.name}"?\n\nThis removes the playlist only.\nMedia files and library tracks will not be deleted.`,
    { okLabel: "Delete" },
  );
  if (!confirmed) return;
  setBulkBusy(true, `Deleting playlist "${playlist.name}"...`);
  try {
    await api(`/api/playlists/${encodeURIComponent(playlist.playlist_id)}`, { method: "DELETE" });
    const deletedName = playlist.name;
    state.selectedPlaylist = null;
    state.playlistDraft = [];
    await loadPlaylists();
    if (!state.selectedPlaylist && state.playlists.length) {
      state.selectedPlaylist = state.playlists[0];
      state.playlistDraft = state.selectedPlaylist.items.map((item) => item.media_id);
      renderPlaylists();
    }
    setPlaylistDirty(false, state.selectedPlaylist ? "Saved" : "Saved");
    $("scanResult").textContent = `Deleted playlist: ${deletedName}`;
  } catch (err) {
    $("scanResult").textContent = `Failed to delete playlist: ${err.message}`;
    console.error("Failed to delete playlist", err);
  } finally {
    setBulkBusy(false);
  }
});

$("addFilteredToPlaylist").addEventListener("click", async () => {
  if (!state.selectedPlaylist?.playlist_id) return alert("Select a playlist first.");
  setBulkBusy(true, "Loading all filtered tracks...");
  try {
    const items = await loadAllFilteredMedia();
    setBulkBusy(false);
    await bulkAddItemsToPlaylist(items, "filtered tracks");
  } catch (err) {
    $("scanResult").textContent = `Failed to load filtered tracks: ${err.message}`;
    console.error("Failed to load filtered tracks", err);
    setBulkBusy(false);
  }
});

$("createPlaylistFromFiltered").addEventListener("click", async () => {
  let filteredItems = [];
  try {
    filteredItems = await loadAllFilteredMedia();
  } catch (err) {
    $("scanResult").textContent = `Failed to load filtered tracks: ${err.message}`;
    console.error("Failed to load filtered tracks", err);
    return;
  }
  const ids = uniqueMediaIds(filteredItems);
  if (!ids.length) return alert("No filtered tracks to add.");
  let trimmed = "";
  setBulkBusy(true, `Creating playlist from ${ids.length} tracks...`);
  try {
    trimmed = requirePlaylistName("creating a playlist from filtered tracks");
    const playlist = await createPlaylist(trimmed);
    const result = await api(`/api/playlists/${encodeURIComponent(playlist.playlist_id)}/items/bulk`, {
      method: "POST",
      body: JSON.stringify({ media_ids: ids }),
    });
    state.selectedPlaylist = { playlist_id: playlist.playlist_id, name: playlist.name, items: [] };
    await loadPlaylists();
    const refreshed = state.playlists.find((entry) => entry.playlist_id === playlist.playlist_id);
    if (refreshed) {
      state.selectedPlaylist = refreshed;
      state.playlistDraft = refreshed.items.map((item) => item.media_id);
    }
    setPlaylistDirty(false, "Saved");
    renderPlaylists();
    $("scanResult").textContent = `Created "${playlist.name}" with ${result.added} tracks. Skipped duplicates: ${result.duplicates}. Errors: ${result.errors}.`;
  } catch (err) {
    $("scanResult").textContent = state.selectedPlaylist?.name === trimmed
      ? `Playlist created, but track addition failed: ${err.message}`
      : `Failed to create playlist: ${err.message}`;
    console.error("Failed to create playlist from filtered tracks", err);
  } finally {
    setBulkBusy(false);
  }
});

$("replacePlaylistWithFiltered").addEventListener("click", async () => {
  if (!state.selectedPlaylist?.playlist_id) return alert("Select a playlist first.");
  setBulkBusy(true, "Loading all filtered tracks...");
  try {
    const items = await loadAllFilteredMedia();
    const ids = uniqueMediaIds(items);
    setBulkBusy(false);
    if (!ids.length) return alert("No filtered tracks to use.");
    const ok = await confirmAction(
      `Replace playlist "${state.selectedPlaylist.name}" with ${ids.length} current filtered tracks?\n\nThis changes the playlist only. Media files and library tracks will not be deleted.`,
      { okLabel: "Replace" },
    );
    if (!ok) return;
    setBulkBusy(true, `Replacing playlist with ${ids.length} tracks...`);
    const payload = {
      playlist_id: state.selectedPlaylist.playlist_id,
      name: state.selectedPlaylist.name,
      media_ids: ids,
    };
    await api(`/api/playlists/${encodeURIComponent(payload.playlist_id)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadPlaylists();
    state.playlistPage = 1;
    setPlaylistDirty(false, "Saved");
    $("scanResult").textContent = `Replaced "${payload.name}" with ${ids.length} filtered tracks.`;
  } catch (err) {
    $("scanResult").textContent = `Failed to replace playlist tracks: ${err.message}`;
    console.error("Failed to replace playlist tracks", err);
  } finally {
    setBulkBusy(false);
  }
});

$("playPause").addEventListener("click", () => {
  if (!state.current && state.queue[0]) return playItem(state.queue[0], state.queue);
  const player = activeElement();
  if (player.paused) {
    player.play()
      .then(() => {
        $("playPause").textContent = "Pause";
      })
      .catch((err) => {
        showPlaybackError(state.current, player, err);
        $("playPause").textContent = "Play";
      });
  } else {
    player.pause();
    $("playPause").textContent = "Play";
  }
});

$("prev").addEventListener("click", () => playNext(-1));
$("next").addEventListener("click", () => playNext(1));
$("shuffle").addEventListener("click", () => {
  setQueue(state.queue.length ? state.queue : state.media, { shuffle: true, autoplay: false });
  $("shuffle").classList.add("primary");
});

$("repeat").addEventListener("click", () => {
  state.repeat = state.repeat === "none" ? "all" : state.repeat === "all" ? "one" : "none";
  $("repeat").textContent = state.repeat === "none" ? "Repeat off" : state.repeat === "all" ? "Repeat all" : "Repeat one";
  $("repeat").classList.toggle("primary", state.repeat !== "none");
});

$("volume").addEventListener("input", () => {
  audio.volume = Number($("volume").value);
  video.volume = Number($("volume").value);
});

$("seek").addEventListener("input", () => {
  const player = activeElement();
  if (player && Number.isFinite(player.duration)) {
    player.currentTime = (Number($("seek").value) / 1000) * player.duration;
  }
});

for (const player of [audio, video]) {
  player.addEventListener("timeupdate", () => {
    if (player !== activeElement()) return;
    $("timeNow").textContent = fmtTime(player.currentTime);
    $("timeTotal").textContent = fmtTime(player.duration);
    $("seek").value = Number.isFinite(player.duration) && player.duration > 0
      ? String(Math.floor((player.currentTime / player.duration) * 1000))
      : "0";
  });
  player.addEventListener("ended", () => playNext(1));
  player.addEventListener("error", () => {
    if (state.current) {
      showPlaybackError(state.current, player);
      state.current.failed = true;
      playNext(1, true);
    }
  });
  player.addEventListener("pause", () => {
    if (player === activeElement()) $("playPause").textContent = "Play";
  });
  player.addEventListener("play", () => {
    if (player === activeElement()) $("playPause").textContent = "Pause";
  });
}

$("csvFile").addEventListener("change", showCsvSelection);

$("exportViewCsv").addEventListener("click", async (event) => {
  event.preventDefault();
  try {
    await downloadCsv(currentTrackExportUrl(), "jinnsp_tracks_view.csv", "exportStatus");
  } catch (err) {
    console.error("Track export failed", err);
  }
});

$("exportCsv").addEventListener("click", async (event) => {
  event.preventDefault();
  try {
    await downloadCsv(legacyTrackExportUrl(), "media-library.csv", "csvResult");
  } catch (err) {
    console.error("Legacy media export failed", err);
    setStatus("csvResult", `<div class="error">${escapeHtml(err.message)}</div>`);
  }
});

$("exportPlaylist").addEventListener("click", async (event) => {
  event.preventDefault();
  if (!state.selectedPlaylist?.playlist_id) return;
  try {
    const url = `/api/playlists/${encodeURIComponent(state.selectedPlaylist.playlist_id)}/export.csv`;
    await downloadCsv(url, "jinnsp_playlist.csv", "playlistStatus");
  } catch (err) {
    console.error("Playlist export failed", err);
    $("playlistStatus").textContent = err.message;
  }
});

$("trackMetadataCsv").addEventListener("change", async () => {
  const file = $("trackMetadataCsv").files[0];
  if (!file) return;
  $("trackImportPanel").classList.remove("hidden");
  $("trackImportState").textContent = "Reading CSV...";
  $("applyTrackImport").disabled = true;
  try {
    $("trackImportState").textContent = "Validating...";
    const form = new FormData();
    form.append("file", file);
    const result = await requestFormJson("/api/media/import-csv/preview", form);
    renderTrackImportPreview(result);
  } catch (err) {
    $("trackImportState").textContent = "Import failed";
    $("trackImportSummary").innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    console.error("Track metadata import preview failed", err);
  }
});

$("applyTrackImport").addEventListener("click", async () => {
  if (!state.trackImportToken) return;
  $("trackImportState").textContent = "Importing...";
  $("applyTrackImport").disabled = true;
  try {
    const form = new FormData();
    form.append("token", state.trackImportToken);
    const result = await requestFormJson("/api/media/import-csv/apply", form);
    $("trackImportState").textContent = "Import complete";
    $("trackImportSummary").innerHTML = [
      summaryLine("updated media rows", result.updated_media_rows),
      summaryLine("unchanged rows", result.unchanged_rows),
      summaryLine("skipped rows", result.skipped_rows),
      summaryLine("synced local/R2 rows", result.synced_local_r2_rows),
      summaryLine("error rows", result.error_rows),
      summaryLine("foreign_key_check", result.foreign_key_check),
      `<div>backup path: ${escapeHtml(result.backup_path || "-")}</div>`,
    ].join("");
    state.trackImportToken = "";
    await loadMedia(true);
    await loadPlaylists();
  } catch (err) {
    $("trackImportState").textContent = "Import failed";
    $("trackImportSummary").innerHTML += `<div class="error">${escapeHtml(err.message)}</div>`;
    console.error("Track metadata import apply failed", err);
    $("applyTrackImport").disabled = false;
  }
});

$("cancelTrackImport").addEventListener("click", () => resetTrackImportPanel());

$("playlistCsv").addEventListener("change", async () => {
  const file = $("playlistCsv").files[0];
  if (!file) return;
  if (!state.selectedPlaylist?.playlist_id) {
    $("playlistCsv").value = "";
    return alert("Select a playlist first.");
  }
  $("playlistImportPanel").classList.remove("hidden");
  $("playlistImportState").textContent = "Reading CSV...";
  $("applyPlaylistImport").disabled = true;
  try {
    $("playlistImportState").textContent = "Validating...";
    const form = new FormData();
    form.append("file", file);
    const result = await requestFormJson(`/api/playlists/${encodeURIComponent(state.selectedPlaylist.playlist_id)}/import-csv/preview`, form);
    renderPlaylistImportPreview(result);
  } catch (err) {
    $("playlistImportState").textContent = "Import failed";
    $("playlistImportSummary").innerHTML = `<div class="error">${escapeHtml(err.message)}</div>`;
    console.error("Playlist import preview failed", err);
  }
});

$("applyPlaylistImport").addEventListener("click", async () => {
  if (!state.playlistImportToken || !state.selectedPlaylist?.playlist_id) return;
  $("playlistImportState").textContent = "Importing...";
  $("applyPlaylistImport").disabled = true;
  try {
    const form = new FormData();
    form.append("token", state.playlistImportToken);
    const result = await requestFormJson(`/api/playlists/${encodeURIComponent(state.selectedPlaylist.playlist_id)}/import-csv/apply`, form);
    $("playlistImportState").textContent = "Import complete";
    $("playlistImportSummary").innerHTML = [
      summaryLine("current items before import", result.current_count),
      summaryLine("playlist items after import", result.imported_count),
      summaryLine("added", result.added_count),
      summaryLine("removed", result.removed_count),
      summaryLine("order changes", result.order_changed_count),
      summaryLine("duplicate media_id", result.duplicate_media_id),
      summaryLine("missing media_id", result.missing_media_id),
      summaryLine("foreign_key_check", result.foreign_key_check),
      `<div>backup path: ${escapeHtml(result.backup_path || "-")}</div>`,
    ].join("");
    state.playlistImportToken = "";
    await loadPlaylists();
    setPlaylistDirty(false, "Saved");
  } catch (err) {
    $("playlistImportState").textContent = "Import failed";
    $("playlistImportSummary").innerHTML += `<div class="error">${escapeHtml(err.message)}</div>`;
    console.error("Playlist import apply failed", err);
    $("applyPlaylistImport").disabled = false;
  }
});

$("cancelPlaylistImport").addEventListener("click", () => resetPlaylistImportPanel());

$("importCsv").addEventListener("click", async () => {
  debugLog("csv:import:click", csvSelectionInfo());
  const file = $("csvFile").files[0];
  if (!file) {
    setStatus("csvResult", `<div class="error">Choose a CSV file.</div>`);
    return;
  }

  const fetchUrl = "/api/import/media";
  const method = "POST";
  debugLog("csv:import:formdata", {
    hasFile: true,
    name: file.name,
    size: file.size,
    type: file.type,
    fetchUrl,
    method,
  });

  try {
    const text = await file.text();
    debugLog("csv:import:file-read", { chars: text.length });
    const response = await fetch(fetchUrl, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ csv: text }),
    });
    const responseText = await response.text();
    debugLog("csv:import:http", { status: response.status, ok: response.ok });
    debugLog("csv:import:response-body", { body: responseText.slice(0, 4000) });

    let result;
    try {
      result = JSON.parse(responseText);
      debugLog("csv:import:json", result);
    } catch (err) {
      debugLog("csv:import:json-error", { message: err.message, body: responseText.slice(0, 4000) });
      setStatus("csvResult", `<div class="error">JSON parse failed: ${escapeHtml(err.message)}</div>`);
      throw err;
    }

    if (!response.ok) {
      const message = result.error || response.statusText || "CSV import failed";
      setStatus("csvResult", `<div class="error">HTTP ${response.status}: ${escapeHtml(message)}</div>`);
      throw new Error(message);
    }

    showCsvResult(result);
    await loadMedia();
    const playableItems = (result.items || []).filter(isPlayable);
    setQueue(playableItems, { autoplay: false });
    selectFirstPlayable(playableItems);
    updateQueueCount();
    $("scanResult").textContent = `CSV import done: total ${result.total_rows ?? 0}, imported ${result.imported ?? 0}, duplicates ${result.duplicates ?? 0}, queued ${result.queued ?? 0}`;
  } catch (err) {
    debugLog("csv:import:catch", { message: err.message, stack: err.stack });
    setStatus("csvResult", `<div class="error">Import failed: ${escapeHtml(err.message)}</div>`);
    throw err;
  }
});

Promise.all([loadMedia(), loadPlaylists(), loadFolders(), loadRemoteLibraries(), loadInvalidMedia()])
  .then(() => {
    $("buildStamp").textContent = `app.js ${BUILD_STAMP}`;
    showCsvSelection();
    setView("folders");
    updateQueueCount();
  })
  .catch((err) => alert(err.message));
