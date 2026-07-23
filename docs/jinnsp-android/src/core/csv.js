(function () {
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
