const STORAGE_KEY = "jinnsp-pwa-state-v1";
const BACKUP_SCHEMA_VERSION = 1;
const CSV_COLUMNS = [
  "media_id",
  "title",
  "creator",
  "media_type",
  "source_type",
  "source",
  "source_url",
  "direct_media_url",
  "genre",
  "bpm",
  "tags",
  "rating",
  "duration",
  "created_at",
  "play_count",
  "last_played",
];

const state = {
  seedTracks: [],
  userTracks: [],
  localSessionTracks: [],
  playlists: [],
  selectedPlaylistId: "",
  queue: [],
  currentIndex: -1,
  repeat: "none",
};

const $ = (id) => document.getElementById(id);
const audio = $("audio");
const video = $("video");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function slugId(prefix = "id") {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeTrack(track) {
  const direct = track.direct_media_url || "";
  const source = track.source || direct || track.source_url || "";
  return {
    media_id: track.media_id || slugId("media"),
    title: track.title || "Untitled",
    creator: track.creator || "unknown creator",
    media_type: track.media_type === "video" ? "video" : "audio",
    source_type: track.source_type || "url",
    source,
    source_url: track.source_url || "",
    direct_media_url: direct,
    genre: track.genre || "",
    bpm: track.bpm || "",
    tags: track.tags || "",
    rating: track.rating || "",
    duration: track.duration || "",
    created_at: track.created_at || new Date().toISOString(),
    play_count: Number(track.play_count || 0),
    last_played: track.last_played || "",
  };
}

function allTracks() {
  const merged = new Map();
  for (const item of [...state.seedTracks, ...state.userTracks, ...state.localSessionTracks]) {
    const track = normalizeTrack(item);
    merged.set(track.media_id, track);
  }
  return [...merged.values()];
}

function selectedPlaylist() {
  return state.playlists.find((playlist) => playlist.playlist_id === state.selectedPlaylistId) || null;
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    userTracks: state.userTracks,
    playlists: state.playlists,
    selectedPlaylistId: state.selectedPlaylistId,
  }));
}

function loadLocalState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    state.userTracks = Array.isArray(data.userTracks) ? data.userTracks.map(normalizeTrack) : [];
    state.playlists = Array.isArray(data.playlists) ? data.playlists : [];
    state.selectedPlaylistId = data.selectedPlaylistId || "";
  } catch (error) {
    $("openStatus").textContent = `Stored data could not be read: ${error.message}`;
  }
}

async function loadSeedData() {
  const [libraryResponse, playlistResponse] = await Promise.all([
    fetch("./data/library.json"),
    fetch("./data/playlists.json"),
  ]);
  const library = libraryResponse.ok ? await libraryResponse.json() : [];
  const playlists = playlistResponse.ok ? await playlistResponse.json() : [];
  state.seedTracks = Array.isArray(library) ? library.map(normalizeTrack) : [];
  if (!state.playlists.length && Array.isArray(playlists)) {
    state.playlists = playlists;
    state.selectedPlaylistId = playlists[0]?.playlist_id || "";
  }
}

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(rows, columns) {
  const lines = [columns.join(",")];
  for (const row of rows) {
    lines.push(columns.map((column) => csvEscape(row[column])).join(","));
  }
  return `\ufeff${lines.join("\r\n")}\r\n`;
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function backupTimestamp(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join("-") + "_" + [
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
  ].join("");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quote = false;
  const input = text.replace(/^\ufeff/, "");
  for (let i = 0; i < input.length; i += 1) {
    const char = input[i];
    const next = input[i + 1];
    if (quote && char === '"' && next === '"') {
      cell += '"';
      i += 1;
    } else if (char === '"') {
      quote = !quote;
    } else if (!quote && char === ",") {
      row.push(cell);
      cell = "";
    } else if (!quote && (char === "\n" || char === "\r")) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell);
  if (row.some((value) => value !== "")) rows.push(row);
  if (!rows.length) return [];
  const headers = rows[0].map((value) => value.trim());
  return rows.slice(1).map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
}

function upsertUserTrack(track) {
  const normalized = normalizeTrack(track);
  const index = state.userTracks.findIndex((item) => item.media_id === normalized.media_id);
  if (index >= 0) state.userTracks[index] = normalized;
  else state.userTracks.push(normalized);
}

function filteredTracks() {
  const q = $("q").value.trim().toLowerCase();
  const mediaType = $("mediaType").value;
  const sourceType = $("sourceType").value;
  const tag = $("tag").value.trim().toLowerCase();
  return allTracks().filter((track) => {
    const haystack = [track.title, track.creator, track.tags, track.source, track.source_url, track.direct_media_url].join(" ").toLowerCase();
    if (q && !haystack.includes(q)) return false;
    if (mediaType && track.media_type !== mediaType) return false;
    if (sourceType && track.source_type !== sourceType) return false;
    if (tag && !String(track.tags || "").toLowerCase().split(/[;, ]+/).includes(tag)) return false;
    return true;
  });
}

function playUrl(track) {
  return track.direct_media_url || track.source || "";
}

function playableTracks(items) {
  return items.filter((item) => Boolean(playUrl(item)));
}

function queueUnique(items) {
  const seen = new Set();
  const unique = [];
  for (const item of playableTracks(items)) {
    const key = item.media_id || item.direct_media_url || item.source || item.source_url;
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    unique.push(item);
  }
  return unique;
}

function setQueue(items, shuffle = false) {
  const nextQueue = queueUnique(items);
  if (shuffle) {
    for (let i = nextQueue.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [nextQueue[i], nextQueue[j]] = [nextQueue[j], nextQueue[i]];
    }
  }
  state.queue = nextQueue;
  state.currentIndex = -1;
  updateNow();
}

function usePlayer(track) {
  const player = track.media_type === "video" ? video : audio;
  const other = track.media_type === "video" ? audio : video;
  other.pause();
  other.removeAttribute("src");
  other.style.display = "none";
  player.style.display = track.media_type === "video" ? "block" : "revert";
  player.src = playUrl(track);
  player.load();
  return player;
}

async function playAt(index) {
  if (!state.queue.length) return;
  if (index < 0) index = state.queue.length - 1;
  if (index >= state.queue.length) {
    if (state.repeat === "all") index = 0;
    else return;
  }
  state.currentIndex = index;
  const track = state.queue[index];
  updateNow(track);
  try {
    await usePlayer(track).play();
    $("playPause").textContent = "Pause";
  } catch (error) {
    $("playerStatus").textContent = `Playback blocked or failed: ${error.message}`;
    $("playPause").textContent = "Play";
  }
}

function playNext(step = 1) {
  if (state.repeat === "one" && state.currentIndex >= 0) return playAt(state.currentIndex);
  return playAt(state.currentIndex + step);
}

function updateNow(track = state.queue[state.currentIndex]) {
  $("nowTitle").textContent = track?.title || "Choose a track";
  $("nowMeta").textContent = track
    ? `${track.creator || "unknown creator"} / ${track.source_type || "-"} / Queue: ${state.queue.length}`
    : `Queue: ${state.queue.length}`;
}

function renderTracks() {
  const items = filteredTracks();
  const total = allTracks().length;
  $("libraryStatus").textContent = items.length === total
    ? `Showing ${items.length} tracks`
    : `Filtered: ${items.length} of ${total} tracks`;
  $("trackList").innerHTML = items.length ? items.map((track) => `
    <article class="item" data-id="${escapeHtml(track.media_id)}">
      <div>
        <div class="item-title">${escapeHtml(track.title)}</div>
        <div class="meta">${escapeHtml(track.creator)} / ${escapeHtml(track.source_type)} / ${escapeHtml(track.media_type)} / ${escapeHtml(track.tags || "no tags")}</div>
        <div class="meta">${escapeHtml(track.source || track.source_url || "-")}</div>
      </div>
      <div class="item-actions">
        <button data-action="play">Play</button>
        <button data-action="add">Add</button>
      </div>
    </article>
  `).join("") : `<div class="status">No tracks match the current filters.</div>`;
}

function renderPlaylists() {
  const playlist = selectedPlaylist();
  $("playlistList").innerHTML = state.playlists.map((item) => `
    <button class="playlist-button ${item.playlist_id === state.selectedPlaylistId ? "active" : ""}" data-id="${escapeHtml(item.playlist_id)}">
      <strong>${escapeHtml(item.name)}</strong>
      <span class="status">${(item.media_ids || []).length} tracks</span>
    </button>
  `).join("");
  $("playlistName").value = playlist?.name || "";
  $("exportPlaylistCsv").disabled = !playlist;
  $("deletePlaylist").disabled = !playlist;
  const query = $("playlistSearch").value.trim().toLowerCase();
  const tracksById = new Map(allTracks().map((track) => [track.media_id, track]));
  const items = (playlist?.media_ids || []).map((id) => tracksById.get(id)).filter(Boolean)
    .filter((track) => !query || [track.title, track.creator, track.source, track.source_url, track.tags].join(" ").toLowerCase().includes(query));
  $("playlistItems").innerHTML = playlist ? items.map((track) => `
    <article class="item" data-id="${escapeHtml(track.media_id)}">
      <div>
        <div class="item-title">${escapeHtml(track.title)}</div>
        <div class="meta">${escapeHtml(track.creator)} / ${escapeHtml(track.source_type)} / ${escapeHtml(track.tags || "no tags")}</div>
      </div>
      <div class="item-actions">
        <button data-action="play">Play</button>
        <button data-action="remove">Remove</button>
      </div>
    </article>
  `).join("") || `<div class="status">No playlist items match.</div>` : `<div class="status">Select or create a playlist.</div>`;
}

function renderAll() {
  renderTracks();
  renderPlaylists();
  updateNow();
}

function exportLibraryCsv() {
  downloadText("jinnsp-library.csv", toCsv(allTracks(), CSV_COLUMNS), "text/csv;charset=utf-8");
  $("libraryStatus").textContent = `Exported ${allTracks().length} tracks.`;
}

async function importMetadataCsv(file) {
  const rows = parseCsv(await file.text());
  const tracksById = new Map(allTracks().map((track) => [track.media_id, track]));
  let updated = 0;
  let skipped = 0;
  for (const row of rows) {
    const base = tracksById.get(row.media_id);
    if (!base) {
      skipped += 1;
      continue;
    }
    const patch = { ...base };
    for (const field of ["title", "creator", "genre", "bpm", "tags", "rating"]) {
      if (Object.prototype.hasOwnProperty.call(row, field)) patch[field] = row[field];
    }
    if (!patch.title.trim()) {
      skipped += 1;
      continue;
    }
    upsertUserTrack(patch);
    updated += 1;
  }
  saveState();
  renderAll();
  $("libraryStatus").textContent = `Imported metadata CSV. Updated: ${updated}. Skipped: ${skipped}.`;
}

function exportPlaylistCsv() {
  const playlist = selectedPlaylist();
  if (!playlist) return;
  const tracksById = new Map(allTracks().map((track) => [track.media_id, track]));
  const rows = (playlist.media_ids || []).map((id, index) => ({
    playlist_id: playlist.playlist_id,
    playlist_name: playlist.name,
    position: index + 1,
    ...(tracksById.get(id) || { media_id: id }),
  }));
  downloadText(`${playlist.name || "playlist"}.csv`, toCsv(rows, ["playlist_id", "playlist_name", "position", ...CSV_COLUMNS]), "text/csv;charset=utf-8");
  $("playlistStatus").textContent = `Exported ${rows.length} playlist tracks.`;
}

async function importPlaylistCsv(file) {
  const playlist = selectedPlaylist();
  if (!playlist) return alert("Select a playlist first.");
  const rows = parseCsv(await file.text())
    .filter((row) => row.media_id)
    .sort((a, b) => Number(a.position || 0) - Number(b.position || 0));
  const known = new Set(allTracks().map((track) => track.media_id));
  const mediaIds = [];
  const seen = new Set();
  let skipped = 0;
  for (const row of rows) {
    if (!known.has(row.media_id) || seen.has(row.media_id)) {
      skipped += 1;
      continue;
    }
    seen.add(row.media_id);
    mediaIds.push(row.media_id);
  }
  playlist.media_ids = mediaIds;
  saveState();
  renderAll();
  $("playlistStatus").textContent = `Imported playlist CSV. Tracks: ${mediaIds.length}. Skipped: ${skipped}. Saved.`;
}

function downloadBackup() {
  const settings = {
    selectedPlaylistId: state.selectedPlaylistId,
    repeat: state.repeat,
  };
  const backup = {
    schemaVersion: BACKUP_SCHEMA_VERSION,
    app: "JinnSP",
    exportedAt: new Date().toISOString(),
    tracks: state.userTracks,
    playlists: state.playlists,
    settings,
  };
  const filename = `JinnSP_Backup_${backupTimestamp()}.jinnsp`;
  downloadText(filename, JSON.stringify(backup, null, 2), "application/octet-stream");
  $("backupStatus").textContent = `Backup downloaded: ${filename}`;
}

function normalizeBackupData(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("This is not a valid JinnSP backup file.");
  }

  if (Object.prototype.hasOwnProperty.call(data, "schemaVersion")) {
    if (data.schemaVersion !== BACKUP_SCHEMA_VERSION) {
      throw new Error(`Unsupported backup schemaVersion: ${data.schemaVersion}`);
    }
    if (!Array.isArray(data.tracks)) throw new Error("Backup is missing tracks.");
    if (!Array.isArray(data.playlists)) throw new Error("Backup is missing playlists.");
    if (!data.settings || typeof data.settings !== "object" || Array.isArray(data.settings)) {
      throw new Error("Backup is missing settings.");
    }
    return {
      tracks: data.tracks,
      playlists: data.playlists,
      settings: data.settings,
      schemaVersion: data.schemaVersion,
    };
  }

  if (Array.isArray(data.userTracks) && Array.isArray(data.playlists)) {
    return {
      tracks: data.userTracks,
      playlists: data.playlists,
      settings: {
        selectedPlaylistId: data.selectedPlaylistId || "",
      },
      schemaVersion: "legacy",
    };
  }

  throw new Error("Backup is missing required JinnSP data.");
}

function validateBackupItems(backup) {
  for (const [index, track] of backup.tracks.entries()) {
    if (!track || typeof track !== "object" || Array.isArray(track)) {
      throw new Error(`Track ${index + 1} is invalid.`);
    }
  }
  for (const [index, playlist] of backup.playlists.entries()) {
    if (!playlist || typeof playlist !== "object" || Array.isArray(playlist)) {
      throw new Error(`Playlist ${index + 1} is invalid.`);
    }
    if (!playlist.playlist_id || !playlist.name || !Array.isArray(playlist.media_ids)) {
      throw new Error(`Playlist ${index + 1} is missing required fields.`);
    }
  }
  return backup;
}

async function restoreBackup(file) {
  let parsed;
  try {
    parsed = JSON.parse(await file.text());
    const backup = validateBackupItems(normalizeBackupData(parsed));
    const counts = {
      tracks: backup.tracks.length,
      playlists: backup.playlists.length,
      settings: Object.keys(backup.settings).length,
    };
    $("backupStatus").textContent = `Backup contains tracks: ${counts.tracks}, playlists: ${counts.playlists}, settings: ${counts.settings}.`;
    const ok = confirm(
      `Restore this JinnSP backup?\n\ntracks: ${counts.tracks}\nplaylists: ${counts.playlists}\nsettings: ${counts.settings}\n\nCurrent browser edits will be replaced.`,
    );
    if (!ok) {
      $("backupStatus").textContent = "Restore canceled. Existing data was not changed.";
      return;
    }
    state.userTracks = backup.tracks.map(normalizeTrack);
    state.playlists = backup.playlists;
    state.selectedPlaylistId = backup.settings.selectedPlaylistId || state.playlists[0]?.playlist_id || "";
    state.repeat = backup.settings.repeat || "none";
    $("repeat").textContent = state.repeat === "none" ? "Repeat off" : state.repeat === "all" ? "Repeat all" : "Repeat one";
    saveState();
    renderAll();
    $("backupStatus").textContent = `Backup restored. tracks: ${counts.tracks}, playlists: ${counts.playlists}, settings: ${counts.settings}.`;
  } catch (error) {
    $("backupStatus").textContent = `Restore failed: ${error.message}`;
  } finally {
    $("restoreBackup").value = "";
  }
}

function trackById(id) {
  return allTracks().find((track) => track.media_id === id);
}

function addToPlaylist(track) {
  const playlist = selectedPlaylist();
  if (!playlist) return alert("Create or select a playlist first.");
  playlist.media_ids ||= [];
  if (!playlist.media_ids.includes(track.media_id)) playlist.media_ids.push(track.media_id);
  saveState();
  renderAll();
  $("playlistStatus").textContent = "Saved";
}

function addFiles(files) {
  const created = [...files].map((file) => normalizeTrack({
    media_id: slugId("local"),
    title: file.name.replace(/\.[^.]+$/, ""),
    creator: "local file",
    media_type: file.type.startsWith("video/") ? "video" : "audio",
    source_type: "local",
    source: URL.createObjectURL(file),
    tags: "session",
  }));
  state.localSessionTracks.push(...created);
  setQueue(created);
  renderAll();
  $("openStatus").textContent = `Opened ${created.length} local files for this session.`;
}

function addUrl() {
  const source = $("urlInput").value.trim();
  if (!source) return;
  const track = normalizeTrack({
    title: source.split("/").pop() || "URL track",
    creator: "URL",
    media_type: $("urlMediaType").value,
    source_type: "url",
    source,
    direct_media_url: source,
    tags: "URL",
  });
  upsertUserTrack(track);
  saveState();
  setQueue([track]);
  renderAll();
  $("openStatus").textContent = `Added URL: ${track.title}`;
}

async function init() {
  loadLocalState();
  await loadSeedData();
  if (!state.playlists.length) {
    state.playlists.push({ playlist_id: slugId("playlist"), name: "New playlist", media_ids: [] });
    state.selectedPlaylistId = state.playlists[0].playlist_id;
  }
  renderAll();
}

$("exportLibraryCsv").addEventListener("click", exportLibraryCsv);
$("importMetadataCsv").addEventListener("change", (event) => event.target.files[0] && importMetadataCsv(event.target.files[0]));
$("exportPlaylistCsv").addEventListener("click", exportPlaylistCsv);
$("importPlaylistCsv").addEventListener("change", (event) => event.target.files[0] && importPlaylistCsv(event.target.files[0]));
$("downloadBackup").addEventListener("click", downloadBackup);
$("restoreBackup").addEventListener("change", (event) => event.target.files[0] && restoreBackup(event.target.files[0]));
$("resetLocalData").addEventListener("click", () => {
  if (!confirm("Reset local edits stored in this browser?")) return;
  localStorage.removeItem(STORAGE_KEY);
  location.reload();
});
$("openFileInput").addEventListener("change", (event) => addFiles(event.target.files));
$("openUrl").addEventListener("click", addUrl);
$("newPlaylist").addEventListener("click", () => {
  const name = prompt("Playlist name");
  if (!name?.trim()) return;
  const playlist = { playlist_id: slugId("playlist"), name: name.trim(), media_ids: [] };
  state.playlists.push(playlist);
  state.selectedPlaylistId = playlist.playlist_id;
  saveState();
  renderAll();
});
$("savePlaylist").addEventListener("click", () => {
  const playlist = selectedPlaylist();
  if (!playlist) return;
  playlist.name = $("playlistName").value.trim() || playlist.name;
  saveState();
  renderAll();
  $("playlistStatus").textContent = "Saved";
});
$("deletePlaylist").addEventListener("click", () => {
  const playlist = selectedPlaylist();
  if (!playlist || !confirm(`Delete playlist "${playlist.name}"?`)) return;
  state.playlists = state.playlists.filter((item) => item.playlist_id !== playlist.playlist_id);
  state.selectedPlaylistId = state.playlists[0]?.playlist_id || "";
  saveState();
  renderAll();
});
$("playFiltered").addEventListener("click", () => {
  setQueue(filteredTracks());
  playAt(0);
});
$("shuffleFiltered").addEventListener("click", () => {
  setQueue(filteredTracks(), true);
  playAt(0);
});
$("addFilteredToPlaylist").addEventListener("click", () => {
  const playlist = selectedPlaylist();
  if (!playlist) return alert("Create or select a playlist first.");
  const before = new Set(playlist.media_ids || []);
  for (const track of filteredTracks()) before.add(track.media_id);
  playlist.media_ids = [...before];
  saveState();
  renderAll();
  $("playlistStatus").textContent = "Saved";
});
$("trackList").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  const item = event.target.closest(".item");
  if (!button || !item) return;
  const track = trackById(item.dataset.id);
  if (!track) return;
  if (button.dataset.action === "play") {
    setQueue([track]);
    playAt(0);
  }
  if (button.dataset.action === "add") addToPlaylist(track);
});
$("playlistList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-id]");
  if (!button) return;
  state.selectedPlaylistId = button.dataset.id;
  saveState();
  renderAll();
});
$("playlistItems").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  const item = event.target.closest(".item");
  const playlist = selectedPlaylist();
  if (!button || !item || !playlist) return;
  const track = trackById(item.dataset.id);
  if (button.dataset.action === "play" && track) {
    setQueue((playlist.media_ids || []).map(trackById).filter(Boolean));
    playAt(state.queue.findIndex((entry) => entry.media_id === track.media_id));
  }
  if (button.dataset.action === "remove") {
    playlist.media_ids = (playlist.media_ids || []).filter((id) => id !== item.dataset.id);
    saveState();
    renderAll();
  }
});
for (const id of ["q", "mediaType", "sourceType", "tag", "playlistSearch"]) {
  $(id).addEventListener("input", renderAll);
  $(id).addEventListener("change", renderAll);
}
$("clearFilters").addEventListener("click", () => {
  for (const id of ["q", "mediaType", "sourceType", "tag"]) $(id).value = "";
  renderAll();
});
$("playPause").addEventListener("click", () => {
  const player = state.queue[state.currentIndex]?.media_type === "video" ? video : audio;
  if (state.currentIndex < 0 && state.queue.length) return playAt(0);
  if (player.paused) player.play();
  else player.pause();
});
$("prev").addEventListener("click", () => playNext(-1));
$("next").addEventListener("click", () => playNext(1));
$("shuffle").addEventListener("click", () => setQueue(state.queue.length ? state.queue : allTracks(), true));
$("repeat").addEventListener("click", () => {
  state.repeat = state.repeat === "none" ? "all" : state.repeat === "all" ? "one" : "none";
  $("repeat").textContent = state.repeat === "none" ? "Repeat off" : state.repeat === "all" ? "Repeat all" : "Repeat one";
});
$("volume").addEventListener("input", () => {
  audio.volume = Number($("volume").value);
  video.volume = Number($("volume").value);
});
for (const player of [audio, video]) {
  player.addEventListener("ended", () => playNext(1));
  player.addEventListener("play", () => $("playPause").textContent = "Pause");
  player.addEventListener("pause", () => $("playPause").textContent = "Play");
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./service-worker.js").catch(() => {});
}

init().catch((error) => {
  $("openStatus").textContent = `Startup failed: ${error.message}`;
});
