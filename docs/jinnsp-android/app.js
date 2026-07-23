/* core/constants.js */
﻿(function () {
  const Core = window.JinnSPCore || (window.JinnSPCore = {});
  Core.STORAGE_KEY = "jinnsp-unified-state-v1";
  Core.LEGACY_WEB_STORAGE_KEY = "jinnsp-pwa-state-v1";
  Core.LEGACY_ANDROID_STORAGE_KEY = "jinnsp-android-state-v1";
  Core.BACKUP_SCHEMA_VERSION = 1;
  Core.AUDIO_EXTENSIONS = [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"];
  Core.VIDEO_EXTENSIONS = [".mp4", ".webm", ".mov", ".m4v", ".ogv"];
  Core.CSV_COLUMNS = [
    "media_id", "title", "creator", "media_type", "source_type", "source", "source_url",
    "direct_media_url", "genre", "bpm", "tags", "rating", "duration", "created_at",
    "play_count", "last_played", "uri", "folder_uri", "access_status"
  ];

  Core.slugId = function slugId(prefix = "id") {
    return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  };

  Core.escapeHtml = function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[char]));
  };

  Core.mediaTypeFromName = function mediaTypeFromName(name = "", fallback = "audio") {
    const lower = String(name || "").toLowerCase();
    if (Core.VIDEO_EXTENSIONS.some((ext) => lower.endsWith(ext))) return "video";
    if (Core.AUDIO_EXTENSIONS.some((ext) => lower.endsWith(ext))) return "audio";
    return fallback === "video" ? "video" : "audio";
  };

  Core.normalizeTrack = function normalizeTrack(track = {}) {
    const direct = track.direct_media_url || "";
    const source = track.source || direct || track.source_url || track.uri || "";
    return {
      media_id: track.media_id || Core.slugId("media"),
      title: track.title || track.name?.replace(/\.[^.]+$/, "") || "Untitled",
      creator: track.creator || (track.source_type === "local" ? "local file" : "unknown creator"),
      media_type: track.media_type === "video" ? "video" : Core.mediaTypeFromName(track.name || track.title || source, track.media_type),
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
      folder_uri: track.folder_uri || "",
      access_status: track.access_status || "ok",
    };
  };

  Core.trackKey = function trackKey(track) {
    return track?.media_id || track?.direct_media_url || track?.source || track?.uri || track?.source_url || "";
  };

  Core.playUrl = function playUrl(track) {
    return track?.direct_media_url || track?.source || track?.uri || "";
  };
})();


/* core/csv.js */
﻿(function () {
  const Core = window.JinnSPCore;

  Core.csvEscape = function csvEscape(value) {
    const text = String(value ?? "");
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };

  Core.toCsv = function toCsv(rows, columns = Core.CSV_COLUMNS) {
    const lines = [columns.join(",")];
    for (const row of rows) lines.push(columns.map((column) => Core.csvEscape(row[column])).join(","));
    return `\ufeff${lines.join("\r\n")}\r\n`;
  };

  Core.parseCsv = function parseCsv(text) {
    const rows = [];
    let row = [];
    let cell = "";
    let quote = false;
    const input = String(text || "").replace(/^\ufeff/, "");
    for (let i = 0; i < input.length; i += 1) {
      const char = input[i];
      const next = input[i + 1];
      if (quote && char === '"' && next === '"') { cell += '"'; i += 1; }
      else if (char === '"') quote = !quote;
      else if (!quote && char === ",") { row.push(cell); cell = ""; }
      else if (!quote && (char === "\n" || char === "\r")) {
        if (char === "\r" && next === "\n") i += 1;
        row.push(cell);
        if (row.some((value) => value !== "")) rows.push(row);
        row = [];
        cell = "";
      } else cell += char;
    }
    row.push(cell);
    if (row.some((value) => value !== "")) rows.push(row);
    if (!rows.length) return [];
    const headers = rows[0].map((value) => value.trim());
    return rows.slice(1).map((values) => Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])));
  };

  Core.libraryCsv = function libraryCsv(tracks) {
    return Core.toCsv(tracks.map(Core.normalizeTrack), Core.CSV_COLUMNS);
  };

  Core.playlistCsv = function playlistCsv(playlist, tracks) {
    const byId = new Map(tracks.map((track) => [track.media_id, Core.normalizeTrack(track)]));
    const rows = (playlist?.media_ids || []).map((id, index) => ({
      playlist_id: playlist.playlist_id,
      playlist_name: playlist.name,
      position: index + 1,
      ...(byId.get(id) || { media_id: id }),
    }));
    return Core.toCsv(rows, ["playlist_id", "playlist_name", "position", ...Core.CSV_COLUMNS]);
  };

  Core.applyMetadataCsv = function applyMetadataCsv(rows, tracks) {
    const byId = new Map(tracks.map((track) => [track.media_id, Core.normalizeTrack(track)]));
    const updates = [];
    let skipped = 0;
    for (const row of rows) {
      const base = byId.get(row.media_id);
      if (!base) { skipped += 1; continue; }
      const patch = { ...base };
      for (const field of ["title", "creator", "genre", "bpm", "tags", "rating", "media_type", "source_type", "source", "source_url", "direct_media_url"]) {
        if (Object.prototype.hasOwnProperty.call(row, field)) patch[field] = row[field];
      }
      if (!String(patch.title || "").trim()) { skipped += 1; continue; }
      updates.push(Core.normalizeTrack(patch));
    }
    return { updates, skipped };
  };

  Core.playlistIdsFromCsv = function playlistIdsFromCsv(rows, tracks) {
    const known = new Set(tracks.map((track) => track.media_id));
    const sorted = rows.filter((row) => row.media_id).sort((a, b) => Number(a.position || 0) - Number(b.position || 0));
    const seen = new Set();
    const mediaIds = [];
    let skipped = 0;
    for (const row of sorted) {
      if (!known.has(row.media_id) || seen.has(row.media_id)) { skipped += 1; continue; }
      seen.add(row.media_id);
      mediaIds.push(row.media_id);
    }
    return { mediaIds, skipped };
  };
})();


/* core/backup.js */
﻿(function () {
  const Core = window.JinnSPCore;

  Core.backupTimestamp = function backupTimestamp(date = new Date()) {
    const pad = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}_${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
  };

  Core.makeBackup = function makeBackup(state) {
    return {
      schemaVersion: Core.BACKUP_SCHEMA_VERSION,
      app: "JinnSP",
      exportedAt: new Date().toISOString(),
      tracks: (state.tracks || []).map(Core.normalizeTrack),
      playlists: state.playlists || [],
      settings: {
        selectedPlaylistId: state.selectedPlaylistId || "",
        repeat: state.repeat || "none",
        folders: state.folders || [],
      },
    };
  };

  Core.normalizeBackup = function normalizeBackup(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error("This is not a valid JinnSP backup file.");
    if (Object.prototype.hasOwnProperty.call(data, "schemaVersion")) {
      if (data.schemaVersion !== Core.BACKUP_SCHEMA_VERSION) throw new Error(`Unsupported backup schemaVersion: ${data.schemaVersion}`);
      if (!Array.isArray(data.tracks)) throw new Error("Backup is missing tracks.");
      if (!Array.isArray(data.playlists)) throw new Error("Backup is missing playlists.");
      return {
        tracks: data.tracks.map(Core.normalizeTrack),
        playlists: data.playlists,
        settings: data.settings && typeof data.settings === "object" ? data.settings : {},
      };
    }
    if (Array.isArray(data.tracks) && Array.isArray(data.playlists)) {
      return { tracks: data.tracks.map(Core.normalizeTrack), playlists: data.playlists, settings: data.settings || {} };
    }
    if (Array.isArray(data.userTracks) && Array.isArray(data.playlists)) {
      return {
        tracks: data.userTracks.map(Core.normalizeTrack),
        playlists: data.playlists,
        settings: { selectedPlaylistId: data.selectedPlaylistId || "" },
      };
    }
    throw new Error("Backup is missing required JinnSP data.");
  };

  Core.validatePlaylists = function validatePlaylists(playlists) {
    for (const [index, playlist] of (playlists || []).entries()) {
      if (!playlist || typeof playlist !== "object" || Array.isArray(playlist)) throw new Error(`Playlist ${index + 1} is invalid.`);
      if (!playlist.playlist_id || !playlist.name || !Array.isArray(playlist.media_ids)) throw new Error(`Playlist ${index + 1} is missing required fields.`);
    }
  };
})();


/* core/library.js */
﻿(function () {
  const Core = window.JinnSPCore;

  Core.mergeTracks = function mergeTracks(baseTracks, incomingTracks) {
    const merged = new Map();
    for (const raw of baseTracks || []) {
      const track = Core.normalizeTrack(raw);
      merged.set(Core.trackKey(track), track);
    }
    for (const raw of incomingTracks || []) {
      const track = Core.normalizeTrack(raw);
      const existingKey = [...merged.keys()].find((key) => {
        const item = merged.get(key);
        return (item.uri || item.source || item.direct_media_url) === (track.uri || track.source || track.direct_media_url);
      });
      merged.set(existingKey || Core.trackKey(track), existingKey ? { ...merged.get(existingKey), ...track, media_id: merged.get(existingKey).media_id } : track);
    }
    return [...merged.values()];
  };

  Core.selectedPlaylist = function selectedPlaylist(state) {
    return (state.playlists || []).find((playlist) => playlist.playlist_id === state.selectedPlaylistId) || null;
  };

  Core.addToPlaylist = function addToPlaylist(playlist, track) {
    if (!playlist || !track) return false;
    playlist.media_ids ||= [];
    if (playlist.media_ids.includes(track.media_id)) return false;
    playlist.media_ids.push(track.media_id);
    return true;
  };

  Core.trackMatchesQuery = function trackMatchesQuery(track, query) {
    if (!query) return true;
    const haystack = [track.title, track.creator, track.tags, track.source, track.source_url, track.direct_media_url, track.genre].join(" ").toLowerCase();
    return haystack.includes(String(query).toLowerCase());
  };

  Core.isFavorite = function isFavorite(track) {
    return String(track.tags || "").toLowerCase().split(/[;, ]+/).includes("favorite") || Number(track.rating || 0) >= 5;
  };

  Core.filterTracks = function filterTracks(tracks, filters = {}) {
    return (tracks || []).map(Core.normalizeTrack).filter((track) => {
      if (!Core.trackMatchesQuery(track, filters.q || "")) return false;
      if (filters.media_type && track.media_type !== filters.media_type) return false;
      if (filters.source_type && track.source_type !== filters.source_type) return false;
      if (filters.tag && !String(track.tags || "").toLowerCase().split(/[;, ]+/).includes(String(filters.tag).toLowerCase())) return false;
      if (filters.scope === "favorite" && !Core.isFavorite(track)) return false;
      if (filters.scope === "local" && track.source_type !== "local") return false;
      if (filters.scope === "url" && track.source_type !== "url") return false;
      return true;
    });
  };

  Core.uniqueQueue = function uniqueQueue(items) {
    const seen = new Set();
    const queue = [];
    for (const raw of items || []) {
      const item = Core.normalizeTrack(raw);
      if (!Core.playUrl(item) || item.access_status === "invalid") continue;
      const key = Core.trackKey(item);
      if (key && seen.has(key)) continue;
      if (key) seen.add(key);
      queue.push(item);
    }
    return queue;
  };
})();


/* platform/adapter.js */
﻿(function () {
  const Core = window.JinnSPCore;
  const CapacitorBridge = window.Capacitor || null;
  const Native = CapacitorBridge?.Plugins?.JinnSPNative || null;
  const NativePreferences = CapacitorBridge?.Plugins?.Preferences || null;
  const isNative = () => Boolean(CapacitorBridge?.isNativePlatform?.());

  async function getRawStorage(key) {
    if (isNative() && NativePreferences) return (await NativePreferences.get({ key })).value;
    return localStorage.getItem(key);
  }

  async function setRawStorage(key, value) {
    if (isNative() && NativePreferences) return NativePreferences.set({ key, value });
    localStorage.setItem(key, value);
  }

  async function removeRawStorage(key) {
    if (isNative() && NativePreferences) return NativePreferences.remove({ key });
    localStorage.removeItem(key);
  }

  async function loadState() {
    const keys = [Core.STORAGE_KEY, Core.LEGACY_ANDROID_STORAGE_KEY, Core.LEGACY_WEB_STORAGE_KEY];
    for (const key of keys) {
      const raw = await getRawStorage(key);
      if (!raw) continue;
      const data = JSON.parse(raw);
      if (Array.isArray(data.tracks)) {
        return {
          tracks: data.tracks.map(Core.normalizeTrack),
          folders: Array.isArray(data.folders) ? data.folders : [],
          playlists: Array.isArray(data.playlists) ? data.playlists : [],
          selectedPlaylistId: data.selectedPlaylistId || "",
          repeat: data.repeat || "none",
        };
      }
      if (Array.isArray(data.userTracks)) {
        return {
          tracks: data.userTracks.map(Core.normalizeTrack),
          folders: [],
          playlists: Array.isArray(data.playlists) ? data.playlists : [],
          selectedPlaylistId: data.selectedPlaylistId || "",
          repeat: data.repeat || "none",
        };
      }
    }
    return { tracks: [], folders: [], playlists: [], selectedPlaylistId: "", repeat: "none" };
  }

  async function saveState(state) {
    await setRawStorage(Core.STORAGE_KEY, JSON.stringify({
      tracks: state.tracks || [],
      folders: state.folders || [],
      playlists: state.playlists || [],
      selectedPlaylistId: state.selectedPlaylistId || "",
      repeat: state.repeat || "none",
    }));
  }

  async function resetState() {
    await removeRawStorage(Core.STORAGE_KEY);
  }

  async function downloadText(filename, content, type = "application/octet-stream") {
    if (isNative() && Native?.saveBackup && filename.toLowerCase().endsWith(".jinnsp")) {
      return Native.saveBackup({ filename, content });
    }
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return { filename };
  }

  function readFileAsText(file) {
    return file.text();
  }

  function chooseTextFile(accept = ".jinnsp,.json") {
    return new Promise((resolve, reject) => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = accept;
      input.onchange = () => {
        const file = input.files?.[0];
        if (!file) reject(new Error("No file selected."));
        else resolve(file.text());
      };
      input.click();
    });
  }

  async function openBackupText() {
    if (isNative() && Native?.openBackup) return (await Native.openBackup()).content;
    return chooseTextFile(".jinnsp,application/json,.json");
  }

  async function pickAudioFiles() {
    if (isNative() && Native?.pickAudioFiles) {
      const result = await Native.pickAudioFiles();
      return (result.items || []).map((item) => Core.normalizeTrack({ ...item, source_type: "local", source: item.uri, tags: item.tags || "Android" }));
    }
    return new Promise((resolve) => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "audio/*,video/*";
      input.multiple = true;
      input.onchange = () => {
        const files = [...(input.files || [])];
        resolve(files.map((file) => Core.normalizeTrack({
          media_id: Core.slugId("local"),
          title: file.name.replace(/\.[^.]+$/, ""),
          creator: "local file",
          media_type: file.type.startsWith("video/") ? "video" : "audio",
          source_type: "local",
          source: URL.createObjectURL(file),
          uri: "",
          tags: "session",
        })));
      };
      input.click();
    });
  }

  async function pickMusicFolder() {
    if (!isNative() || !Native?.pickMusicFolder) throw new Error("Folder picker is available in the Android app.");
    return Native.pickMusicFolder();
  }

  async function listFolderAudio(uri) {
    if (!isNative() || !Native?.listFolderAudio) throw new Error("Folder scanning is available in the Android app.");
    const result = await Native.listFolderAudio({ uri });
    return (result.items || []).map((item) => Core.normalizeTrack({
      ...item,
      source_type: "local",
      source: item.uri,
      folder_uri: uri,
      tags: item.tags || "Android folder",
    }));
  }

  async function updateMediaSession(track, isPlaying, queueSize, index) {
    if (!isNative() || !Native?.updateMediaSession) return;
    try {
      await Native.updateMediaSession({ title: track?.title || "JinnSP", creator: track?.creator || "", isPlaying: Boolean(isPlaying), queueSize, index });
    } catch (error) {
      console.warn("MediaSession update failed", error);
    }
  }

  function registerServiceWorker() {
    if (isNative()) return;
    if ("serviceWorker" in navigator) navigator.serviceWorker.register("./service-worker.js").catch(() => {});
  }

  window.JinnSPPlatform = {
    isNative,
    loadState,
    saveState,
    resetState,
    downloadText,
    readFileAsText,
    openBackupText,
    pickAudioFiles,
    pickMusicFolder,
    listFolderAudio,
    updateMediaSession,
    registerServiceWorker,
  };
})();


/* playback/playback.js */
﻿(function () {
  const Core = window.JinnSPCore;
  const Platform = () => window.JinnSPPlatform;

  function createPlayback(elements, state, onUpdate) {
    const audio = elements.audio;
    const video = elements.video;

    function activeElement(track = state.queue[state.currentIndex]) {
      return track?.media_type === "video" ? video : audio;
    }

    function stopOther(track) {
      const other = track?.media_type === "video" ? audio : video;
      if (!other) return;
      other.pause();
      other.removeAttribute("src");
      other.style.display = "none";
    }

    function setQueue(items, shuffle = false) {
      const queue = Core.uniqueQueue(items);
      if (shuffle) {
        for (let i = queue.length - 1; i > 0; i -= 1) {
          const j = Math.floor(Math.random() * (i + 1));
          [queue[i], queue[j]] = [queue[j], queue[i]];
        }
      }
      state.queue = queue;
      state.currentIndex = -1;
      onUpdate?.();
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
      stopOther(track);
      const player = activeElement(track);
      if (!player) return;
      player.style.display = track.media_type === "video" ? "block" : "revert";
      player.src = Core.playUrl(track);
      player.load();
      onUpdate?.();
      try {
        await player.play();
        await Platform().updateMediaSession(track, true, state.queue.length, state.currentIndex);
      } catch (error) {
        elements.status.textContent = `Playback failed: ${error.message}`;
        await Platform().updateMediaSession(track, false, state.queue.length, state.currentIndex);
      }
    }

    function playNext(step = 1) {
      if (state.repeat === "one" && state.currentIndex >= 0) return playAt(state.currentIndex);
      return playAt(state.currentIndex + step);
    }

    function toggle() {
      const player = activeElement();
      if (state.currentIndex < 0 && state.queue.length) return playAt(0);
      if (!player) return;
      if (player.paused) return player.play();
      player.pause();
    }

    for (const player of [audio, video]) {
      if (!player) continue;
      player.addEventListener("ended", () => playNext(1));
      player.addEventListener("play", () => { onUpdate?.(); Platform().updateMediaSession(state.queue[state.currentIndex], true, state.queue.length, state.currentIndex); });
      player.addEventListener("pause", () => { onUpdate?.(); Platform().updateMediaSession(state.queue[state.currentIndex], false, state.queue.length, state.currentIndex); });
    }

    window.JinnSPMediaControls = { play: () => activeElement()?.play(), pause: () => activeElement()?.pause(), next: () => playNext(1), prev: () => playNext(-1) };

    return { setQueue, playAt, playNext, toggle, activeElement };
  }

  window.JinnSPPlayback = { createPlayback };
})();


/* app.js */
﻿const CapacitorBridge = window.Capacitor || null;
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
const VIDEO_EXTENSIONS = [".mp4", ".webm", ".mov", ".m4v", ".ogv"];
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
  playbackSource: { type: "Library", name: "Queue", count: 0 },
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
  if (VIDEO_EXTENSIONS.some((ext) => lower.endsWith(ext))) return "video";
  if (AUDIO_EXTENSIONS.some((ext) => lower.endsWith(ext))) return "audio";
  return "audio";
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

function setQueue(items, shuffle = false, source = null) {
  const queue = queueUnique(items);
  if (shuffle) {
    for (let i = queue.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [queue[i], queue[j]] = [queue[j], queue[i]];
    }
  }
  state.queue = queue;
  state.currentIndex = -1;
  state.playbackSource = source || { type: "Library", name: shuffle ? "Shuffle" : "Queue", count: queue.length };
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
  const source = state.playbackSource || { type: "Library", name: "Queue", count: state.queue.length };
  const sourceLabel = `${source.type || "Library"}: ${source.name || "Queue"} / ${source.count ?? state.queue.length} tracks`;
  const meta = track
    ? `${track.creator || "unknown creator"} / ${track.source_type || "-"} / ${sourceLabel}`
    : `${sourceLabel} / Queue: ${state.queue.length}`;
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

function canDeleteTrack(track) {
  return state.tracks.some((item) => item.media_id === track.media_id);
}

function renderTrackCard(track, options = {}) {
  const disabled = track.access_status === "invalid" || !playUrl(track) ? "disabled" : "";
  const addButton = options.hideAdd ? "" : `<button class="kebab" data-action="add" title="Add to playlist">＋</button>`;
  const deleteButton = options.deletable ? `<button class="kebab danger" data-action="delete" title="Delete from library">Del</button>` : "";
  const removeButton = options.remove ? `<button class="kebab" data-action="remove" title="Remove from playlist">−</button>` : "";
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
        ${addButton}${removeButton}${deleteButton}
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
    ? items.map((track) => renderTrackCard(track, { deletable: canDeleteTrack(track) })).join("")
    : `<div class="status">No tracks match.</div>`;
}

function playlistTracks(playlist) {
  const byId = new Map(allTracks().map((track) => [track.media_id, track]));
  return (playlist?.media_ids || []).map((id) => byId.get(id)).filter(Boolean);
}

function filteredPlaylistItems(playlist) {
  const query = $("playlistSearch").value.trim().toLowerCase();
  const tag = $("playlistTag")?.value.trim().toLowerCase() || "";
  const sourceType = $("playlistSource")?.value || "";
  return playlistTracks(playlist).filter((track) => {
    if (query && !trackMatchesQuery(track, query)) return false;
    if (tag && !String(track.tags || "").toLowerCase().split(/[;, ]+/).includes(tag)) return false;
    if (sourceType && track.source_type !== sourceType) return false;
    return true;
  });
}

function renderPlaylists() {
  const playlist = selectedPlaylist();
  const playing = state.playbackSource?.type === "Playlist" ? state.playbackSource.name : "";
  $("playlistList").innerHTML = state.playlists.map((item) => {
    const count = (item.media_ids || []).length;
    const isSelected = item.playlist_id === state.selectedPlaylistId;
    const isPlaying = playing && item.name === playing;
    return `
      <article class="playlist-card ${isSelected ? "active" : ""} ${isPlaying ? "playing" : ""}" data-id="${escapeHtml(item.playlist_id)}">
        <div class="playlist-card-main">
          <strong>${escapeHtml(item.name)}</strong>
          <small class="status">${count} tracks ${isPlaying ? " / ● Playing" : isSelected ? " / ✓ Selected" : ""}</small>
        </div>
        <div class="playlist-actions">
          <button data-action="play">Play</button>
          <button data-action="shuffle">Shuffle</button>
          <button data-action="open">Open/Edit</button>
        </div>
      </article>`;
  }).join("");
  $("playlistName").value = playlist?.name || "";
  const items = filteredPlaylistItems(playlist);
  const total = playlistTracks(playlist).length;
  $("playlistStatus").textContent = playlist ? `Showing ${items.length} of ${total} tracks` : "Create or select a playlist.";
  $("playlistItems").innerHTML = playlist
    ? items.map((track) => renderTrackCard(track, { hideAdd: true, remove: true })).join("") || `<div class="status">No playlist items match.</div>`
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
    ? tracks.slice(0, 40).map((track) => renderTrackCard(track, { deletable: canDeleteTrack(track) })).join("") || `<div class="status">No search results.</div>`
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

function pickWebFiles() {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "audio/*,video/*,.mp3,.wav,.ogg,.m4a,.aac,.flac,.mp4,.webm,.mov,.m4v,.ogv";
    input.multiple = true;
    input.style.position = "fixed";
    input.style.left = "-10000px";
    document.body.appendChild(input);
    input.addEventListener("change", () => {
      const files = [...(input.files || [])];
      input.remove();
      resolve(files.map((file) => {
        const objectUrl = URL.createObjectURL(file);
        return normalizeTrack({
          media_id: slugId("local"),
          title: file.name.replace(/\.[^.]+$/, ""),
          creator: "local file",
          media_type: file.type.startsWith("video/") ? "video" : mediaTypeFromName(file.name),
          source_type: "local",
          source: objectUrl,
          uri: objectUrl,
          tags: "web local",
          duration: "",
          access_status: "ok",
        });
      }));
    }, { once: true });
    input.addEventListener("cancel", () => { input.remove(); reject(new Error("No file selected.")); }, { once: true });
    input.click();
  });
}

async function pickFiles() {
  let items = [];
  if (isNative() && Native) {
    const result = await Native.pickAudioFiles();
    items = (result.items || []).map((item) => ({
      ...item,
      media_id: item.media_id || slugId("local"),
      source_type: "local",
      source: item.uri,
      tags: item.tags || "Android",
    }));
  } else {
    items = await pickWebFiles();
  }
  if (!items.length) return;
  upsertTracks(items);
  await saveState();
  renderAll();
  $("syncStatus").textContent = `Added ${items.length} file(s).`;
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

function deleteTrack(track) {
  if (!canDeleteTrack(track)) return;
  if (!confirm(`Delete "${track.title}" from library?`)) return;
  const url = track.source || track.uri || "";
  if (url.startsWith("blob:")) URL.revokeObjectURL(url);
  state.tracks = state.tracks.filter((item) => item.media_id !== track.media_id);
  state.playlists = state.playlists.map((playlist) => ({
    ...playlist,
    media_ids: (playlist.media_ids || []).filter((id) => id !== track.media_id),
  }));
  state.queue = state.queue.filter((item) => item.media_id !== track.media_id);
  if (state.currentIndex >= state.queue.length) state.currentIndex = state.queue.length - 1;
  saveState().then(renderAll);
  $("syncStatus").textContent = "Track deleted.";
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
    format: "JinnSP Backup",
    version: BACKUP_SCHEMA_VERSION,
    app: "JinnSP",
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

function normalizeBackup(data) {
  if (!data || typeof data !== "object") throw new Error("Unsupported JinnSP backup.");
  if (Object.prototype.hasOwnProperty.call(data, "schemaVersion") && data.schemaVersion !== BACKUP_SCHEMA_VERSION) {
    throw new Error(`Unsupported JinnSP backup schemaVersion: ${data.schemaVersion}`);
  }
  const tracks = Array.isArray(data.tracks) ? data.tracks : Array.isArray(data.userTracks) ? data.userTracks : null;
  if (!tracks) throw new Error("Backup is missing tracks.");
  if (!Array.isArray(data.playlists)) throw new Error("Backup is missing playlists.");
  return {
    schemaVersion: BACKUP_SCHEMA_VERSION,
    tracks: tracks.map(normalizeTrack),
    playlists: data.playlists,
    settings: data.settings && typeof data.settings === "object" ? data.settings : {
      selectedPlaylistId: data.selectedPlaylistId || "",
      repeat: data.repeat || "none",
      folders: Array.isArray(data.folders) ? data.folders : [],
    },
  };
}

function readBackupFileWeb() {
  return new Promise((resolve, reject) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "";
    input.style.position = "fixed";
    input.style.left = "-10000px";
    document.body.appendChild(input);
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      input.remove();
      if (!file) return reject(new Error("No backup selected."));
      file.text().then(resolve, reject);
    }, { once: true });
    input.addEventListener("cancel", () => { input.remove(); reject(new Error("No backup selected.")); }, { once: true });
    input.click();
  });
}

async function downloadBackup() {
  const backup = makeBackup();
  const filename = `JinnSP_Backup_${backupTimestamp()}.jinnsp.json`;
  const content = JSON.stringify(backup, null, 2);
  if (isNative() && Native) {
    await Native.saveBackup({ filename, content });
  } else {
    const blob = new Blob([content], { type: "application/json" });
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
    data = JSON.parse(await readBackupFileWeb());
  }
  const backup = normalizeBackup(data);
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
$("playFiltered").addEventListener("click", () => { const items = filteredTracks(); setQueue(items, false, { type: "Library", name: "Filtered tracks", count: items.length }); playAt(0); });
$("shuffleFiltered").addEventListener("click", () => { const items = filteredTracks(); setQueue(items, true, { type: "Library", name: "Filtered shuffle", count: items.length }); playAt(0); });
function handleTrackListClick(event) {
  const button = event.target.closest("button");
  const item = event.target.closest(".track-item");
  if (!button || !item) return;
  const track = allTracks().find((entry) => entry.media_id === item.dataset.id);
  if (!track) return;
  if (button.dataset.action === "play") {
    setQueue([track], false, { type: "Library", name: "Single track", count: 1 });
    playAt(0);
    setTab("now");
  }
  if (button.dataset.action === "add") addToPlaylist(track);
  if (button.dataset.action === "delete") deleteTrack(track);
  if (button.dataset.action === "more") alert(`${track.title}\n${track.source || track.uri || track.direct_media_url || ""}`);
}
$("trackList").addEventListener("click", handleTrackListClick);
$("searchResults").addEventListener("click", handleTrackListClick);
$("playlistList").addEventListener("click", async (event) => {
  const card = event.target.closest("[data-id]");
  if (!card) return;
  const playlist = state.playlists.find((item) => item.playlist_id === card.dataset.id);
  if (!playlist) return;
  const action = event.target.closest("button")?.dataset.action || "open";
  if (action === "play" || action === "shuffle") {
    state.selectedPlaylistId = playlist.playlist_id;
    const items = playlistTracks(playlist);
    setQueue(items, action === "shuffle", { type: "Playlist", name: playlist.name, count: items.length });
    renderAll();
    playAt(0);
    setTab("now");
    return;
  }
  state.selectedPlaylistId = playlist.playlist_id;
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
    setQueue(playlistTracks(playlist), false, { type: "Playlist", name: playlist.name, count: (playlist.media_ids || []).length });
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
for (const id of ["q", "sourceType", "tag", "playlistSearch", "playlistTag", "playlistSource", "globalSearch"]) {
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



