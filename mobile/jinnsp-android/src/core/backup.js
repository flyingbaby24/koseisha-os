(function () {
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
