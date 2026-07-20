const CapacitorBridge = window.Capacitor || null;
const Native = CapacitorBridge?.Plugins?.JinnSPNative || null;
const Preferences = CapacitorBridge?.Plugins?.Preferences || {
  async get({ key }) {
    return { value: localStorage.getItem(key) };
  },
  async set({ key, value }) {
    localStorage.setItem(key, value);
  },
  async remove({ key }) {
    localStorage.removeItem(key);
  },
};
const isNative = () => Boolean(CapacitorBridge?.isNativePlatform?.());
const STORAGE_KEY = "jinnsp-android-state-v1";
const BACKUP_SCHEMA_VERSION = 1;
const AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"];
let libraryScope = "";

const state = {
  seedTracks: [],
  tracks: [],
  folders: [],
  playlists: [],
  selectedPlaylistId: "",
  queue: [],
  currentIndex: -1,
  repeat: "none",
};

const $ = (id) => document.getElementById(id);
const audio = $("audio");

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

function mediaTypeFromName(name = "") {
  const lower = name.toLowerCase();
  return AUDIO_EXTENSIONS.some((ext) => lower.endsWith(ext)) ? "audio" : "audio";
}

function normalizeTrack(track) {
  const direct = track.direct_media_url || "";
  const source = track.source || direct || track.source_url || track.uri || "";
  return {
    media_id: track.media_id || slugId("media"),
    title: track.title || track.name?.replace(/\.[^.]+$/, "") || "Untitled",
    creator: track.creator || (track.source_type === "local" ? "local file" : "unknown creator"),
    media_type: track.media_type || mediaTypeFromName(track.name || track.title || source),
    source_type: track.source_type || "url",
    source,
    source_url: track.source_url || "",
    direct_media_url: direct,
    uri: track.uri || source,
    genre: track.genre || "",
    bpm: track.bpm || "",
    tags: track.tags || "",
    rating: track.rating || "",
    duration: track.duration || "",
    created_at: track.created_at || new Date().toISOString(),
    play_count: Number(track.play_count || 0),
    last_played: track.last_played || "",
    access_status: track.access_status || "ok",
  };
}

function allTracks() {
  const merged = new Map();
  for (const raw of [...state.seedTracks, ...state.tracks]) {
    const track = normalizeTrack(raw);
    merged.set(track.media_id, track);
  }
  return [...merged.values()];
}

function selectedPlaylist() {
  return state.playlists.find((playlist) => playlist.playlist_id === state.selectedPlaylistId) || null;
}

async function saveState() {
  await Preferences.set({
    key: STORAGE_KEY,
    value: JSON.stringify({
      tracks: state.tracks,
      folders: state.folders,
      playlists: state.playlists,
      selectedPlaylistId: state.selectedPlaylistId,
      repeat: state.repeat,
    }),
  });
  $("syncStatus").textContent = "Saved";
}

async function loadState() {
  const { value } = await Preferences.get({ key: STORAGE_KEY });
  if (!value) return;
  const data = JSON.parse(value);
  state.tracks = Array.isArray(data.tracks) ? data.tracks.map(normalizeTrack) : [];
  state.folders = Array.isArray(data.folders) ? data.folders : [];
  state.playlists = Array.isArray(data.playlists) ? data.playlists : [];
  state.selectedPlaylistId = data.selectedPlaylistId || "";
  state.repeat = data.repeat || "none";
}

async function loadSeedData() {
  try {
    const response = await fetch("./data/library.json");
    const library = response.ok ? await response.json() : [];
    state.seedTracks = Array.isArray(library) ? library.map(normalizeTrack) : [];
  } catch {
    state.seedTracks = [];
  }
}

function trackMatchesQuery(track, query) {
  if (!query) return true;
  const haystack = [
    track.title,
    track.creator,
    track.tags,
    track.source,
    track.source_url,
    track.direct_media_url,
    track.genre,
  ].join(" ").toLowerCase();
  return haystack.includes(query.toLowerCase());
}

function isFavorite(track) {
  return String(track.tags || "").toLowerCase().split(/[;, ]+/).includes("favorite") || Number(track.rating || 0) >= 5;
}

function filteredTracks() {
  const q = $("q").value.trim().toLowerCase();
  const sourceType = $("sourceType").value || (libraryScope === "local" || libraryScope === "url" ? libraryScope : "");
  const tag = $("tag").value.trim().toLowerCase();
  return allTracks().filter((track) => {
    if (!trackMatchesQuery(track, q)) return false;
    if (sourceType && track.source_type !== sourceType) return false;
    if (tag && !String(track.tags || "").toLowerCase().split(/[;, ]+/).includes(tag)) return false;
    if (libraryScope === "favorite" && !isFavorite(track)) return false;
    return true;
  });
}

function playUrl(track) {
  return track.direct_media_url || track.source || track.uri || "";
}

function queueUnique(items) {
  const seen = new Set();
  const unique = [];
  for (const item of items.map(normalizeTrack)) {
    const url = playUrl(item);
    if (!url || item.access_status === "invalid") continue;
    const key = item.media_id || item.direct_media_url || item.source || item.uri || item.source_url;
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    unique.push(item);
  }
  return unique;
}

function setQueue(items, shuffle = false) {
  const queue = queueUnique(items);
  if (shuffle) {
    for (let i = queue.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [queue[i], queue[j]] = [queue[j], queue[i]];
    }
  }
  state.queue = queue;
  state.currentIndex = -1;
  updateNow();
}

async function notifyNative(track, isPlaying) {
  if (!isNative() || !Native) return;
  try {
    await Native.updateMediaSession({
      title: track?.title || "JinnSP",
      creator: track?.creator || "",
      isPlaying: Boolean(isPlaying),
      queueSize: state.queue.length,
      index: state.currentIndex,
    });
  } catch (error) {
    console.warn("MediaSession update failed", error);
  }
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
  audio.src = playUrl(track);
  audio.load();
  updateNow(track);
  try {
    await audio.play();
    $("playPause").textContent = "Pause";
    $("miniPlay").textContent = "Pause";
    await notifyNative(track, true);
  } catch (error) {
    $("playerStatus").textContent = `Playback failed: ${error.message}`;
    await notifyNative(track, false);
  }
}

function playNext(step = 1) {
  if (state.repeat === "one" && state.currentIndex >= 0) return playAt(state.currentIndex);
  return playAt(state.currentIndex + step);
}

function updateNow(track = state.queue[state.currentIndex]) {
  const title = track?.title || "Choose a track";
  const meta = track
    ? `${track.creator || "unknown creator"} / ${track.source_type || "-"} / Queue: ${state.queue.length}`
    : `Queue: ${state.queue.length}`;
  $("nowTitle").textContent = title;
  $("nowMeta").textContent = meta;
  $("miniTitle").textContent = title;
  $("miniMeta").textContent = meta;
  const artworkState = track ? "mascot-playing" : "mascot-idle";
  for (const id of ["nowArtwork", "miniArtwork"]) {
    const el = $(id);
    if (!el) continue;
    el.classList.remove("mascot-idle", "mascot-playing", "mascot-searching", "mascot-success");
    el.classList.add(artworkState);
  }
}

function trackDurationLabel(track) {
  if (!track.duration) return "--:--";
  const value = Number(track.duration);
  if (!Number.isFinite(value)) return String(track.duration);
  const mins = Math.floor(value / 60);
  const secs = String(Math.floor(value % 60)).padStart(2, "0");
  return `${mins}:${secs}`;
}

function renderTrackCard(track, options = {}) {
  const disabled = track.access_status === "invalid" ? "disabled" : "";
  const addButton = options.hideAdd ? "" : `<button class="kebab" data-action="add" title="Add to playlist">＋</button>`;
  const removeButton = options.remove ? `<button class="kebab" data-action="remove" title="Remove">−</button>` : "";
  return `
    <article class="track-item" data-id="${escapeHtml(track.media_id)}">
      <button class="thumb" data-action="play" ${disabled} aria-label="Play ${escapeHtml(track.title)}"></button>
      <div class="track-main">
        <div class="item-title">${escapeHtml(track.title)}</div>
        <div class="meta">${escapeHtml(track.creator)} / ${escapeHtml(track.source_type)} / ${escapeHtml(track.tags || "no tags")}</div>
        <div class="meta">${track.access_status === "invalid" ? "Access lost / " : ""}${escapeHtml(track.source || track.uri || track.direct_media_url || "-")}</div>
      </div>
      <div class="track-side">
        <span>${escapeHtml(trackDurationLabel(track))}</span>
        ${addButton}${removeButton}
        <button class="kebab" data-action="more" title="More">...</button>
      </div>
    </article>
  `;
}

function renderTracks() {
  const items = filteredTracks();
  $("libraryStatus").textContent = items.length === allTracks().length
    ? `${items.length} tracks`
    : `Filtered: ${items.length} of ${allTracks().length}`;
  $("trackList").innerHTML = items.length
    ? items.map((track) => renderTrackCard(track)).join("")
    : `<div class="status">No tracks match.</div>`;
}

function renderPlaylists() {
  const playlist = selectedPlaylist();
  $("playlistList").innerHTML = state.playlists.map((item) => `
    <button class="playlist-button ${item.playlist_id === state.selectedPlaylistId ? "active" : ""}" data-id="${escapeHtml(item.playlist_id)}">
      <span><strong>${escapeHtml(item.name)}</strong><br><small class="status">${(item.media_ids || []).length} tracks</small></span>
      <span>›</span>
    </button>
  `).join("");
  $("playlistName").value = playlist?.name || "";
  const query = $("playlistSearch").value.trim().toLowerCase();
  const byId = new Map(allTracks().map((track) => [track.media_id, track]));
  const items = (playlist?.media_ids || []).map((id) => byId.get(id)).filter(Boolean)
    .filter((track) => !query || trackMatchesQuery(track, query));
  $("playlistItems").innerHTML = playlist
    ? items.map((track) => renderTrackCard(track, { hideAdd: true, remove: true })).join("") || `<div class="status">No playlist items.</div>`
    : `<div class="status">Create or select a playlist.</div>`;
}

function renderFolders() {
  $("folderList").innerHTML = state.folders.length ? state.folders.map((folder) => `
    <article class="folder-card">
      <strong>${escapeHtml(folder.name || "Music folder")}</strong>
      <div class="meta">${escapeHtml(folder.uri)}</div>
      <div class="quick-actions">
        <button data-folder="${escapeHtml(folder.uri)}" data-action="rescan">Rescan</button>
      </div>
    </article>
  `).join("") : `<div class="status">No music folders selected.</div>`;
}

function renderSearch() {
  const input = $("globalSearch");
  if (!input) return;
  const query = input.value.trim();
  const tracks = allTracks().filter((track) => trackMatchesQuery(track, query));
  const playlists = state.playlists.filter((playlist) => !query || playlist.name.toLowerCase().includes(query.toLowerCase()));
  $("searchStatus").textContent = query
    ? `${tracks.length} tracks / ${playlists.length} playlists`
    : "Search across tracks and playlists.";
  $("searchResults").innerHTML = query
    ? tracks.slice(0, 40).map((track) => renderTrackCard(track)).join("") || `<div class="status">No search results.</div>`
    : `<div class="status">Type to search your JinnSP library.</div>`;
}

function renderAll() {
  renderTracks();
  renderPlaylists();
  renderFolders();
  renderSearch();
  updateNow();
}

function upsertTracks(tracks) {
  const merged = new Map(state.tracks.map((track) => [track.media_id, track]));
  for (const track of tracks.map(normalizeTrack)) {
    const key = track.media_id || track.uri || track.source;
    const existing = [...merged.values()].find((item) => (item.uri || item.source) === (track.uri || track.source));
    if (existing) merged.set(existing.media_id, { ...existing, ...track, media_id: existing.media_id });
    else merged.set(key, track);
  }
  state.tracks = [...merged.values()];
}

async function addUrl() {
  const source = $("urlInput").value.trim();
  if (!source) return;
  const track = normalizeTrack({
    title: source.split("/").pop() || "URL track",
    creator: source.includes("media.jinn-project.com") ? "flyingbaby" : "URL",
    source_type: "url",
    source,
    direct_media_url: source,
    tags: source.includes("media.jinn-project.com") ? "R2" : "URL",
  });
  upsertTracks([track]);
  await saveState();
  setQueue([track]);
  renderAll();
}

async function pickFiles() {
  if (isNative() && Native) {
    const result = await Native.pickAudioFiles();
    upsertTracks((result.items || []).map((item) => ({
      ...item,
      media_id: item.media_id || slugId("local"),
      source_type: "local",
      source: item.uri,
      tags: item.tags || "Android",
    })));
  } else {
    alert("Android file picker is available in the app build.");
  }
  await saveState();
  renderAll();
}

async function scanFolder(folderUri = "") {
  const result = await Native.listFolderAudio({ uri: folderUri });
  upsertTracks((result.items || []).map((item) => ({
    ...item,
    media_id: item.media_id || slugId("local"),
    source_type: "local",
    source: item.uri,
    folder_uri: folderUri,
    tags: item.tags || "Android folder",
  })));
  await saveState();
  renderAll();
  $("syncStatus").textContent = `Scanned ${result.items?.length || 0} tracks`;
}

async function restoreFoldersOnStartup() {
  if (!isNative() || !Native || !state.folders.length) return;
  for (const folder of state.folders) {
    try {
      await scanFolder(folder.uri);
    } catch {
      state.tracks = state.tracks.map((track) => (
        track.folder_uri === folder.uri ? { ...track, access_status: "invalid" } : track
      ));
    }
  }
  await saveState();
}

async function pickFolder() {
  if (!isNative() || !Native) {
    alert("Android folder picker is available in the app build.");
    return;
  }
  const result = await Native.pickMusicFolder();
  const folder = { uri: result.uri, name: result.name || "Music folder" };
  state.folders = state.folders.filter((item) => item.uri !== folder.uri).concat(folder);
  await scanFolder(folder.uri);
}

function addToPlaylist(track) {
  const playlist = selectedPlaylist();
  if (!playlist) return alert("Create or select a playlist first.");
  playlist.media_ids ||= [];
  if (!playlist.media_ids.includes(track.media_id)) playlist.media_ids.push(track.media_id);
  return saveState().then(renderAll);
}

function backupTimestamp(date = new Date()) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

function makeBackup() {
  return {
    schemaVersion: BACKUP_SCHEMA_VERSION,
    app: "JinnSP Android",
    exportedAt: new Date().toISOString(),
    tracks: state.tracks,
    playlists: state.playlists,
    settings: {
      selectedPlaylistId: state.selectedPlaylistId,
      repeat: state.repeat,
      folders: state.folders,
    },
  };
}

function validateBackup(data) {
  if (!data || typeof data !== "object" || data.schemaVersion !== BACKUP_SCHEMA_VERSION) {
    throw new Error("Unsupported JinnSP backup.");
  }
  if (!Array.isArray(data.tracks)) throw new Error("Backup is missing tracks.");
  if (!Array.isArray(data.playlists)) throw new Error("Backup is missing playlists.");
  if (!data.settings || typeof data.settings !== "object") throw new Error("Backup is missing settings.");
  return data;
}

async function downloadBackup() {
  const backup = makeBackup();
  const filename = `JinnSP_Backup_${backupTimestamp()}.jinnsp`;
  const content = JSON.stringify(backup, null, 2);
  if (isNative() && Native) {
    await Native.saveBackup({ filename, content });
  } else {
    const blob = new Blob([content], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  $("backupStatus").textContent = `Backup saved: ${filename}`;
}

async function restoreBackup() {
  let data;
  if (isNative() && Native) {
    const result = await Native.openBackup();
    data = JSON.parse(result.content);
  } else {
    alert("Restore backup is available in the Android app build.");
    return;
  }
  const backup = validateBackup(data);
  const counts = {
    tracks: backup.tracks.length,
    playlists: backup.playlists.length,
    settings: Object.keys(backup.settings).length,
  };
  $("backupStatus").textContent = `Backup contains tracks: ${counts.tracks}, playlists: ${counts.playlists}, settings: ${counts.settings}.`;
  if (!confirm(`Restore backup?\n\ntracks: ${counts.tracks}\nplaylists: ${counts.playlists}\nsettings: ${counts.settings}`)) return;
  state.tracks = backup.tracks.map(normalizeTrack);
  state.playlists = backup.playlists;
  state.folders = Array.isArray(backup.settings.folders) ? backup.settings.folders : [];
  state.selectedPlaylistId = backup.settings.selectedPlaylistId || state.playlists[0]?.playlist_id || "";
  state.repeat = backup.settings.repeat || "none";
  await saveState();
  renderAll();
  $("backupStatus").textContent = "Backup restored.";
}

function setTab(name) {
  for (const view of document.querySelectorAll(".view")) view.classList.remove("active");
  const view = $(`view-${name}`);
  if (view) view.classList.add("active");
  for (const tab of document.querySelectorAll(".tabs button, .rail-nav button")) tab.classList.toggle("active", tab.dataset.tab === name);
}

async function init() {
  await loadSeedData();
  await loadState();
  if (!state.playlists.length) {
    state.playlists.push({ playlist_id: slugId("playlist"), name: "Jinn", media_ids: [] });
    state.selectedPlaylistId = state.playlists[0].playlist_id;
  }
  $("repeat").textContent = state.repeat === "none" ? "Repeat off" : state.repeat === "all" ? "Repeat all" : "Repeat one";
  await restoreFoldersOnStartup();
  renderAll();
  $("syncStatus").textContent = isNative() ? "Android ready" : "Web preview";
}

for (const nav of document.querySelectorAll(".tabs, .rail-nav")) {
  nav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tab]");
    if (button) setTab(button.dataset.tab);
  });
}
$("openNow").addEventListener("click", () => setTab("now"));
$("miniOpen").addEventListener("click", () => setTab("now"));
$("toggleFilters").addEventListener("click", () => $("filters").classList.toggle("collapsed"));
$("pickFiles").addEventListener("click", () => pickFiles().catch((error) => $("syncStatus").textContent = error.message));
$("pickFolder").addEventListener("click", () => pickFolder().catch((error) => $("syncStatus").textContent = error.message));
$("addUrl").addEventListener("click", () => addUrl().catch((error) => $("syncStatus").textContent = error.message));
$("playFiltered").addEventListener("click", () => { setQueue(filteredTracks()); playAt(0); });
$("shuffleFiltered").addEventListener("click", () => { setQueue(filteredTracks(), true); playAt(0); });
function handleTrackListClick(event) {
  const button = event.target.closest("button");
  const item = event.target.closest(".track-item");
  if (!button || !item) return;
  const track = allTracks().find((entry) => entry.media_id === item.dataset.id);
  if (!track) return;
  if (button.dataset.action === "play") {
    setQueue([track]);
    playAt(0);
    setTab("now");
  }
  if (button.dataset.action === "add") addToPlaylist(track);
  if (button.dataset.action === "more") alert(`${track.title}\n${track.source || track.uri || track.direct_media_url || ""}`);
}
$("trackList").addEventListener("click", handleTrackListClick);
$("searchResults").addEventListener("click", handleTrackListClick);
$("playlistList").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-id]");
  if (!button) return;
  state.selectedPlaylistId = button.dataset.id;
  await saveState();
  renderAll();
});
$("playlistItems").addEventListener("click", (event) => {
  const button = event.target.closest("button");
  const item = event.target.closest(".track-item");
  const playlist = selectedPlaylist();
  if (!button || !item || !playlist) return;
  const track = allTracks().find((entry) => entry.media_id === item.dataset.id);
  if (button.dataset.action === "play" && track) {
    setQueue((playlist.media_ids || []).map((id) => allTracks().find((entry) => entry.media_id === id)).filter(Boolean));
    playAt(state.queue.findIndex((entry) => entry.media_id === track.media_id));
    setTab("now");
  }
  if (button.dataset.action === "remove") {
    playlist.media_ids = playlist.media_ids.filter((id) => id !== item.dataset.id);
    saveState().then(renderAll);
  }
});
$("newPlaylist").addEventListener("click", async () => {
  const name = prompt("Playlist name");
  if (!name?.trim()) return;
  const playlist = { playlist_id: slugId("playlist"), name: name.trim(), media_ids: [] };
  state.playlists.push(playlist);
  state.selectedPlaylistId = playlist.playlist_id;
  await saveState();
  renderAll();
});
$("savePlaylist").addEventListener("click", async () => {
  const playlist = selectedPlaylist();
  if (!playlist) return;
  playlist.name = $("playlistName").value.trim() || playlist.name;
  await saveState();
  renderAll();
  $("playlistStatus").textContent = "Saved";
});
$("deletePlaylist").addEventListener("click", async () => {
  const playlist = selectedPlaylist();
  if (!playlist || !confirm(`Delete playlist "${playlist.name}"?`)) return;
  state.playlists = state.playlists.filter((item) => item.playlist_id !== playlist.playlist_id);
  state.selectedPlaylistId = state.playlists[0]?.playlist_id || "";
  await saveState();
  renderAll();
});
$("downloadBackup").addEventListener("click", () => downloadBackup().catch((error) => $("backupStatus").textContent = error.message));
$("restoreBackup").addEventListener("click", () => restoreBackup().catch((error) => $("backupStatus").textContent = `Restore failed: ${error.message}`));
$("resetLocalData").addEventListener("click", async () => {
  if (!confirm("Reset JinnSP Android data?")) return;
  await Preferences.remove({ key: STORAGE_KEY });
  location.reload();
});
$("folderList").addEventListener("click", (event) => {
  const button = event.target.closest("[data-folder]");
  if (button) scanFolder(button.dataset.folder).catch((error) => $("syncStatus").textContent = error.message);
});
for (const id of ["q", "sourceType", "tag", "playlistSearch", "globalSearch"]) {
  $(id).addEventListener("input", renderAll);
  $(id).addEventListener("change", renderAll);
}
$("clearFilters").addEventListener("click", () => {
  $("q").value = "";
  $("sourceType").value = "";
  $("tag").value = "";
  libraryScope = "";
  for (const button of document.querySelectorAll("#libraryScope button")) button.classList.toggle("active", button.dataset.scope === "");
  renderAll();
});
$("playPause").addEventListener("click", () => {
  if (state.currentIndex < 0 && state.queue.length) return playAt(0);
  if (audio.paused) audio.play();
  else audio.pause();
});
$("miniPlay").addEventListener("click", () => $("playPause").click());
$("prev").addEventListener("click", () => playNext(-1));
$("next").addEventListener("click", () => playNext(1));
$("shuffle").addEventListener("click", () => setQueue(state.queue.length ? state.queue : allTracks(), true));
$("repeat").addEventListener("click", async () => {
  state.repeat = state.repeat === "none" ? "all" : state.repeat === "all" ? "one" : "none";
  $("repeat").textContent = state.repeat === "none" ? "Repeat off" : state.repeat === "all" ? "Repeat all" : "Repeat one";
  await saveState();
});
audio.addEventListener("ended", () => playNext(1));
audio.addEventListener("play", () => {
  $("playPause").textContent = "Pause";
  $("miniPlay").textContent = "Pause";
  notifyNative(state.queue[state.currentIndex], true);
});
audio.addEventListener("pause", () => {
  $("playPause").textContent = "Play";
  $("miniPlay").textContent = "Play";
  notifyNative(state.queue[state.currentIndex], false);
});

window.JinnSPMediaControls = {
  play: () => audio.play(),
  pause: () => audio.pause(),
  next: () => playNext(1),
  prev: () => playNext(-1),
};

init().catch((error) => {
  $("syncStatus").textContent = `Startup failed: ${error.message}`;
});

const libraryScopeEl = $("libraryScope");
if (libraryScopeEl) {
  libraryScopeEl.addEventListener("click", (event) => {
    const button = event.target.closest("[data-scope]");
    if (!button) return;
    libraryScope = button.dataset.scope || "";
    if (libraryScope === "local" || libraryScope === "url") $("sourceType").value = libraryScope;
    if (!libraryScope) $("sourceType").value = "";
    for (const item of libraryScopeEl.querySelectorAll("button")) item.classList.toggle("active", item === button);
    renderAll();
  });
}

for (const button of document.querySelectorAll("[data-search-chip]")) {
  button.addEventListener("click", () => {
    $("globalSearch").value = button.dataset.searchChip || "";
    renderSearch();
  });
}

const favoriteNow = $("favoriteNow");
if (favoriteNow) {
  favoriteNow.addEventListener("click", async () => {
    const current = state.queue[state.currentIndex];
    if (!current) return;
    const track = state.tracks.find((item) => item.media_id === current.media_id);
    const target = track || current;
    const tags = new Set(String(target.tags || "").split(/[;, ]+/).filter(Boolean));
    tags.add("favorite");
    target.tags = [...tags].join(" ");
    if (!track) upsertTracks([target]);
    await saveState();
    renderAll();
  });
}
