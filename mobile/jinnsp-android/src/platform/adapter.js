(function () {
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
