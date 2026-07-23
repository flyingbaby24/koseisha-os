(function () {
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
