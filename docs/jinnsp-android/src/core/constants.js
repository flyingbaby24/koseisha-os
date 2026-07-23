(function () {
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
