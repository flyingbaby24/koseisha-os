(function () {
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
