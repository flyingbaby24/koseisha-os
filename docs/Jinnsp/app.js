const STORAGE_KEY = "jinnsp:pwa:v1";
const BUILD_STAMP = "2026-07-19T11:30:00+09:00";

const state = {
  seedTracks: [],
  seedPlaylists: [],
  userTracks: [],
  localSessionTracks: [],
  playlists: [],
  selectedPlaylistId: "",
  queue: [],
  currentIndex: -1,
  repeat: "none",
  deferredInstallPrompt: null,
};

const $ = (id) => document.getElementById(id);
const audio = $("audio");
const video = $("video");

function uid(prefix = "id") {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`;
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

function splitTags(tags) {
  return String(tags || "")
    .split(/[,\s]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function saveLocalState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    userTracks: state.userTracks,
    playlists: state.playlists,
    selectedPlaylistId: state.selectedPlaylistId,
  }));
}

function loadLocalState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    state.userTracks = Array.isArray(saved.userTracks) ? saved.userTracks : [];
    state.playlists = Array.isArray(saved.playlists) ? saved.playlists : [];
    state.selectedPlaylistId = saved.selectedPlaylistId || "";
  } catch {
    state.userTracks = [];
    state.playlists = [];
  }
}

async function loadJson(path, fallback) {
  try {
    const response = await fetch(path, { cache: "no-cache" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (err) {
    console.warn(`Failed to load ${path}`, err);
    return fallback;
  }
}

function normalizeTrack(raw) {
  const direct = raw.direct_media_url || raw.play_url || "";
  const source = raw.source || direct || raw.source_url || "";
  return {
    media_id: raw.media_id || uid("media"),
    title: raw.title || "Untitled",
    creator: raw.creator || "",
    media_type: raw.media_type === "video" ? "video" : "audio",
    source_type: raw.source_type || (source.startsWith("blob:") ? "local" : "url"),
    source,
    source_url: raw.source_url || "",
    direct_media_url: direct,
    play_url: raw.play_url || direct || source,
    genre: raw.genre || "",
    bpm: raw.bpm ?? "",
    tags: raw.tags || "",
    rating: Number(raw.rating || 0),
    duration: raw.duration || "",
    created_at: raw.created_at || new Date().toISOString(),
    play_count: Number(raw.play_count || 0),
    last_played: raw.last_played || "",
  };
}

function allTracks() {
  const seen = new Set();
  return [...state.seedTracks, ...state.userTracks, ...state.localSessionTracks]
    .map(normalizeTrack)
    .filter((track) => {
      const key = track.media_id || track.play_url || track.source;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

function activePlayer() {
  const item = state.queue[state.currentIndex];
  return item?.media_type === "video" ? video : audio;
}

function filteredTracks() {
  const q = $("q").value.trim().toLowerCase();
  const mediaType = $("mediaType").value;
  const sourceType = $("sourceType").value;
  const genre = $("genre").value.trim().toLowerCase();
  const tag = $("tag").value.trim().toLowerCase();
  const bpmMin = Number($("bpmMin").value || NaN);
  const bpmMax = Number($("bpmMax").value || NaN);
  const rating = Number($("rating").value || 0);

  return allTracks().filter((track) => {
    const text = [track.title, track.creator, track.source, track.source_url, track.direct_media_url, track.genre, track.tags]
      .join(" ")
      .toLowerCase();
    if (q && !text.includes(q)) return false;
    if (mediaType && track.media_type !== mediaType) return false;
    if (sourceType && track.source_type !== sourceType) return false;
    if (genre && !String(track.genre || "").toLowerCase().includes(genre)) return false;
    if (tag && !splitTags(track.tags).some((entry) => entry.toLowerCase().includes(tag))) return false;
    if (Number.isFinite(bpmMin) && !(Number(track.bpm) >= bpmMin)) return false;
    if (Number.isFinite(bpmMax) && !(Number(track.bpm) <= bpmMax)) return false;
    if (rating && Number(track.rating || 0) < rating) return false;
    return true;
  });
}

function queueKey(item) {
  return item.media_id || item.direct_media_url || item.source || item.source_url || item.play_url;
}

function uniquePlayable(items) {
  const seen = new Set();
  return items.filter((item) => {
    const normalized = normalizeTrack(item);
    const key = queueKey(normalized);
    if (!normalized.play_url || seen.has(key)) return false;
    seen.add(key);
    return true;
  }).map(normalizeTrack);
}

function shuffled(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function setStatus(message) {
  $("statusLine").textContent = message;
}

function setQueue(items, { shuffle = false, autoplay = true } = {}) {
  state.queue = shuffle ? shuffled(uniquePlayable(items)) : uniquePlayable(items);
  state.currentIndex = state.queue.length ? 0 : -1;
  updateNow();
  if (autoplay && state.queue.length) playIndex(0);
}

async function playIndex(index) {
  if (!state.queue.length) return;
  if (index < 0 || index >= state.queue.length) return;
  state.currentIndex = index;
  const item = state.queue[index];
  const player = item.media_type === "video" ? video : audio;
  const other = item.media_type === "video" ? audio : video;
  other.pause();
  other.removeAttribute("src");
  video.style.display = item.media_type === "video" ? "block" : "none";
  audio.style.display = item.media_type === "audio" ? "block" : "none";
  player.src = item.play_url;
  player.volume = Number($("volume").value);
  player.load();
  item.play_count = Number(item.play_count || 0) + 1;
  item.last_played = new Date().toISOString();
  updateNow();
  renderTracks();
  try {
    await player.play();
    $("playPause").textContent = "Pause";
  } catch (err) {
    $("playPause").textContent = "Play";
    setStatus(`Playback is ready. Press Play if the browser blocked autoplay. ${err.message || ""}`);
  }
}

function nextIndex(direction = 1) {
  if (!state.queue.length) return -1;
  if (state.repeat === "one") return state.currentIndex;
  const next = state.currentIndex + direction;
  if (next >= 0 && next < state.queue.length) return next;
  return state.repeat === "all" ? (direction > 0 ? 0 : state.queue.length - 1) : -1;
}

function playNext(direction = 1) {
  const index = nextIndex(direction);
  if (index === -1) {
    $("playPause").textContent = "Play";
    return;
  }
  playIndex(index);
}

function updateNow() {
  const item = state.queue[state.currentIndex];
  $("nowTitle").textContent = item ? item.title : "Nothing selected";
  $("nowMeta").textContent = item
    ? `${item.creator || "unknown creator"} / ${item.media_type} / Queue ${state.currentIndex + 1} of ${state.queue.length}`
    : `Queue: ${state.queue.length}`;
}

function itemMeta(item) {
  return [
    item.creator || "unknown creator",
    item.source_type,
    item.media_type,
    item.genre,
    item.tags,
    item.bpm ? `${item.bpm} BPM` : "",
    item.rating ? `${item.rating} stars` : "",
  ].filter(Boolean).join(" / ");
}

function renderTracks() {
  const tracks = filteredTracks();
  $("trackStats").textContent = tracks.length === allTracks().length
    ? `Showing ${tracks.length} tracks`
    : `Filtered: ${tracks.length} of ${allTracks().length} tracks`;
  $("mediaList").innerHTML = tracks.length
    ? tracks.map((item) => `
      <article class="item" data-id="${escapeHtml(item.media_id)}">
        <div class="meta">
          <strong>${escapeHtml(item.title)}</strong>
          <small title="${escapeHtml(item.source || item.play_url)}">${escapeHtml(itemMeta(item))}</small>
          <small>${escapeHtml(item.source || item.source_url || item.play_url)}</small>
        </div>
        <div class="item-actions">
          <button data-action="play" data-id="${escapeHtml(item.media_id)}">Play</button>
          <button data-action="queue" data-id="${escapeHtml(item.media_id)}">Queue</button>
          <button data-action="add" data-id="${escapeHtml(item.media_id)}">Add</button>
          ${state.userTracks.some((track) => track.media_id === item.media_id) ? `<button class="danger" data-action="delete-track" data-id="${escapeHtml(item.media_id)}">Del</button>` : ""}
        </div>
      </article>
    `).join("")
    : `<div class="item"><div class="meta"><strong>No tracks match the current filters.</strong><small>Add a URL or clear filters.</small></div></div>`;
}

function selectedPlaylist() {
  return state.playlists.find((playlist) => playlist.playlist_id === state.selectedPlaylistId) || null;
}

function renderPlaylists() {
  const selected = selectedPlaylist();
  $("playlistList").innerHTML = state.playlists.length
    ? state.playlists.map((playlist) => `
      <button class="playlist-button${playlist.playlist_id === state.selectedPlaylistId ? " active" : ""}" data-playlist="${escapeHtml(playlist.playlist_id)}">
        <span><strong>${escapeHtml(playlist.name)}</strong><br /><small>${playlist.media_ids.length} items</small></span>
      </button>
    `).join("")
    : `<div class="item"><div class="meta"><strong>No playlists yet</strong><small>Create one with New.</small></div></div>`;

  $("playlistName").value = selected?.name || "";
  $("playlistStats").textContent = selected ? `${selected.name}: ${selected.media_ids.length} items` : "No playlist selected";
  const tracks = allTracks();
  const items = selected
    ? selected.media_ids.map((id) => tracks.find((track) => track.media_id === id)).filter(Boolean)
    : [];
  $("playlistItems").innerHTML = items.length
    ? items.map((item) => `
      <article class="item">
        <div class="meta">
          <strong>${escapeHtml(item.title)}</strong>
          <small>${escapeHtml(itemMeta(item))}</small>
        </div>
        <div class="item-actions">
          <button data-action="play" data-id="${escapeHtml(item.media_id)}">Play</button>
          <button class="danger" data-action="remove" data-id="${escapeHtml(item.media_id)}">Remove</button>
        </div>
      </article>
    `).join("")
    : `<div class="item"><div class="meta"><strong>No playlist tracks</strong><small>Add tracks from the library.</small></div></div>`;
}

function renderAll() {
  renderTracks();
  renderPlaylists();
  updateNow();
}

function findTrack(id) {
  return allTracks().find((track) => track.media_id === id);
}

function addTrackToSelectedPlaylist(id) {
  let playlist = selectedPlaylist();
  if (!playlist) {
    playlist = { playlist_id: uid("playlist"), name: "JinnSP", media_ids: [] };
    state.playlists.push(playlist);
    state.selectedPlaylistId = playlist.playlist_id;
  }
  if (!playlist.media_ids.includes(id)) playlist.media_ids.push(id);
  saveLocalState();
  renderPlaylists();
}

function createUrlTrack({ persist }) {
  const url = $("urlInput").value.trim();
  if (!/^https?:\/\//i.test(url)) {
    setStatus("Enter a direct HTTP/HTTPS media URL.");
    return null;
  }
  const pathName = (() => {
    try {
      return decodeURIComponent(new URL(url).pathname.split("/").pop() || "Remote media");
    } catch {
      return "Remote media";
    }
  })();
  const title = pathName.replace(/\.[a-z0-9]+$/i, "") || "Remote media";
  const item = normalizeTrack({
    media_id: uid("url"),
    title,
    creator: "",
    media_type: $("urlMediaType").value,
    source_type: "url",
    source: url,
    direct_media_url: url,
    tags: "URL",
  });
  if (persist) {
    state.userTracks.push(item);
    saveLocalState();
    renderTracks();
    setStatus(`Added "${item.title}" to library.`);
  }
  return item;
}

function exportJson() {
  const blob = new Blob([JSON.stringify({
    library: [...state.seedTracks, ...state.userTracks],
    playlists: state.playlists,
    exported_at: new Date().toISOString(),
  }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "jinnsp-library.json";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function importJson(file) {
  const text = await file.text();
  const payload = JSON.parse(text);
  const importedTracks = Array.isArray(payload.library) ? payload.library : (Array.isArray(payload.tracks) ? payload.tracks : []);
  const importedPlaylists = Array.isArray(payload.playlists) ? payload.playlists : [];
  state.userTracks = importedTracks.map(normalizeTrack);
  state.playlists = importedPlaylists.map((playlist) => ({
    playlist_id: playlist.playlist_id || uid("playlist"),
    name: playlist.name || "Imported playlist",
    media_ids: Array.isArray(playlist.media_ids) ? [...new Set(playlist.media_ids)] : [],
  }));
  state.selectedPlaylistId = state.playlists[0]?.playlist_id || "";
  saveLocalState();
  renderAll();
  setStatus(`Imported ${state.userTracks.length} tracks and ${state.playlists.length} playlists.`);
}

function setupEvents() {
  for (const id of ["q", "mediaType", "sourceType", "genre", "tag", "bpmMin", "bpmMax", "rating"]) {
    $(id).addEventListener("input", renderTracks);
    $(id).addEventListener("change", renderTracks);
  }

  $("clearFilters").addEventListener("click", () => {
    for (const id of ["q", "mediaType", "sourceType", "genre", "tag", "bpmMin", "bpmMax", "rating"]) $(id).value = "";
    renderTracks();
  });

  $("openUrl").addEventListener("click", () => {
    const item = createUrlTrack({ persist: false });
    if (item) setQueue([item], { autoplay: true });
  });

  $("saveUrl").addEventListener("click", () => createUrlTrack({ persist: true }));

  $("fileInput").addEventListener("change", (event) => {
    const files = Array.from(event.target.files || []);
    const items = files.map((file) => normalizeTrack({
      media_id: uid("local"),
      title: file.name.replace(/\.[a-z0-9]+$/i, ""),
      creator: "",
      media_type: file.type.startsWith("video/") ? "video" : "audio",
      source_type: "local",
      source: file.name,
      play_url: URL.createObjectURL(file),
      tags: "Local",
    }));
    state.localSessionTracks.push(...items);
    setQueue(items, { autoplay: false });
    renderTracks();
    setStatus(`Queued ${items.length} local session files.`);
  });

  $("mediaList").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const item = findTrack(button.dataset.id);
    if (!item) return;
    if (button.dataset.action === "play") setQueue([item], { autoplay: true });
    if (button.dataset.action === "queue") {
      state.queue = uniquePlayable([...state.queue, item]);
      updateNow();
      setStatus(`Queue: ${state.queue.length}`);
    }
    if (button.dataset.action === "add") addTrackToSelectedPlaylist(item.media_id);
    if (button.dataset.action === "delete-track") {
      state.userTracks = state.userTracks.filter((track) => track.media_id !== item.media_id);
      for (const playlist of state.playlists) playlist.media_ids = playlist.media_ids.filter((id) => id !== item.media_id);
      saveLocalState();
      renderAll();
    }
  });

  $("playlistList").addEventListener("click", (event) => {
    const button = event.target.closest("[data-playlist]");
    if (!button) return;
    state.selectedPlaylistId = button.dataset.playlist;
    saveLocalState();
    renderPlaylists();
  });

  $("playlistItems").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const item = findTrack(button.dataset.id);
    if (!item) return;
    if (button.dataset.action === "play") setQueue([item], { autoplay: true });
    if (button.dataset.action === "remove") {
      const playlist = selectedPlaylist();
      if (!playlist) return;
      playlist.media_ids = playlist.media_ids.filter((id) => id !== item.media_id);
      saveLocalState();
      renderPlaylists();
    }
  });

  $("newPlaylist").addEventListener("click", () => {
    const playlist = { playlist_id: uid("playlist"), name: "New playlist", media_ids: [] };
    state.playlists.unshift(playlist);
    state.selectedPlaylistId = playlist.playlist_id;
    saveLocalState();
    renderPlaylists();
  });

  $("savePlaylist").addEventListener("click", () => {
    const playlist = selectedPlaylist();
    if (!playlist) return;
    playlist.name = $("playlistName").value.trim() || playlist.name;
    saveLocalState();
    renderPlaylists();
  });

  $("deletePlaylist").addEventListener("click", () => {
    const playlist = selectedPlaylist();
    if (!playlist) return;
    state.playlists = state.playlists.filter((entry) => entry.playlist_id !== playlist.playlist_id);
    state.selectedPlaylistId = state.playlists[0]?.playlist_id || "";
    saveLocalState();
    renderPlaylists();
  });

  $("playFiltered").addEventListener("click", () => setQueue(filteredTracks(), { autoplay: true }));
  $("shuffleFiltered").addEventListener("click", () => setQueue(filteredTracks(), { shuffle: true, autoplay: true }));
  $("addFilteredToPlaylist").addEventListener("click", () => {
    const ids = filteredTracks().map((track) => track.media_id);
    if (!ids.length) return;
    let playlist = selectedPlaylist();
    if (!playlist) {
      playlist = { playlist_id: uid("playlist"), name: "JinnSP", media_ids: [] };
      state.playlists.push(playlist);
      state.selectedPlaylistId = playlist.playlist_id;
    }
    playlist.media_ids = [...new Set([...playlist.media_ids, ...ids])];
    saveLocalState();
    renderPlaylists();
    setStatus(`Added filtered tracks to "${playlist.name}".`);
  });

  $("prev").addEventListener("click", () => playNext(-1));
  $("next").addEventListener("click", () => playNext(1));
  $("playPause").addEventListener("click", () => {
    const player = activePlayer();
    if (!state.queue.length) return;
    if (player.paused) {
      player.play();
      $("playPause").textContent = "Pause";
    } else {
      player.pause();
      $("playPause").textContent = "Play";
    }
  });
  $("shuffle").addEventListener("click", () => setQueue(state.queue.length ? state.queue : filteredTracks(), { shuffle: true, autoplay: false }));
  $("repeat").addEventListener("click", () => {
    state.repeat = state.repeat === "none" ? "all" : state.repeat === "all" ? "one" : "none";
    $("repeat").textContent = state.repeat === "none" ? "Repeat off" : state.repeat === "all" ? "Repeat all" : "Repeat one";
  });
  $("seek").addEventListener("input", () => {
    const player = activePlayer();
    if (player && Number.isFinite(player.duration)) player.currentTime = (Number($("seek").value) / 1000) * player.duration;
  });
  $("volume").addEventListener("input", () => {
    audio.volume = Number($("volume").value);
    video.volume = Number($("volume").value);
  });

  for (const player of [audio, video]) {
    player.addEventListener("timeupdate", () => {
      if (player !== activePlayer()) return;
      $("timeNow").textContent = fmtTime(player.currentTime);
      $("timeTotal").textContent = fmtTime(player.duration);
      $("seek").value = Number.isFinite(player.duration) && player.duration > 0
        ? String(Math.floor((player.currentTime / player.duration) * 1000))
        : "0";
    });
    player.addEventListener("ended", () => playNext(1));
    player.addEventListener("play", () => { if (player === activePlayer()) $("playPause").textContent = "Pause"; });
    player.addEventListener("pause", () => { if (player === activePlayer()) $("playPause").textContent = "Play"; });
    player.addEventListener("error", () => {
      const item = state.queue[state.currentIndex];
      setStatus(`Could not play: ${item?.title || "unknown media"}`);
      playNext(1);
    });
  }

  $("exportLibrary").addEventListener("click", exportJson);
  $("importLibrary").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) importJson(file).catch((err) => setStatus(`Import failed: ${err.message}`));
  });
  $("resetLocalData").addEventListener("click", () => {
    localStorage.removeItem(STORAGE_KEY);
    state.userTracks = [];
    state.playlists = state.seedPlaylists.map((playlist) => ({ ...playlist, media_ids: [...(playlist.media_ids || [])] }));
    state.selectedPlaylistId = state.playlists[0]?.playlist_id || "";
    saveLocalState();
    renderAll();
  });
}

async function setupPwa() {
  if ("serviceWorker" in navigator) {
    try {
      await navigator.serviceWorker.register("./service-worker.js", { scope: "./" });
      $("pwaStatus").textContent = "Offline shell is cached.";
    } catch (err) {
      $("pwaStatus").textContent = `Service worker failed: ${err.message}`;
    }
  } else {
    $("pwaStatus").textContent = "Service workers are not supported in this browser.";
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    state.deferredInstallPrompt = event;
    $("installApp").disabled = false;
    $("pwaStatus").textContent = "Install is available.";
  });

  $("installApp").addEventListener("click", async () => {
    if (!state.deferredInstallPrompt) return;
    state.deferredInstallPrompt.prompt();
    await state.deferredInstallPrompt.userChoice;
    state.deferredInstallPrompt = null;
    $("installApp").disabled = true;
  });
}

async function init() {
  $("buildStamp").textContent = `PWA ${BUILD_STAMP}`;
  loadLocalState();
  const libraryPayload = await loadJson("./data/library.json", { tracks: [] });
  const playlistPayload = await loadJson("./data/playlists.json", { playlists: [] });
  state.seedTracks = (libraryPayload.tracks || libraryPayload.items || []).map(normalizeTrack);
  state.seedPlaylists = (playlistPayload.playlists || []).map((playlist) => ({
    playlist_id: playlist.playlist_id || uid("playlist"),
    name: playlist.name || "Seed playlist",
    media_ids: Array.isArray(playlist.media_ids) ? playlist.media_ids : [],
  }));
  if (!state.playlists.length) {
    state.playlists = state.seedPlaylists.map((playlist) => ({ ...playlist, media_ids: [...playlist.media_ids] }));
    state.selectedPlaylistId = state.playlists[0]?.playlist_id || "";
    saveLocalState();
  }
  setupEvents();
  renderAll();
  setupPwa();
}

init().catch((err) => {
  console.error(err);
  setStatus(`Startup failed: ${err.message}`);
});
