/* Podcast: mini-player on chapter pages + full player on listen.html
 * Pure-client (localStorage + fetch). Loaded on every page.
 *
 * Audio sources live in assets/podcast/{slug}.{mp3,webm}; per-episode
 * manifests at assets/podcast/{slug}.json (turns w/ start/end times);
 * master playlist at assets/podcast/audio_manifest.json.
 *
 * Storage keys (namespaced apart from bookmarks.js):
 *   id-podcast-progress  {[slug]: {currentTime, duration, completed, lastPlayed}}
 *   id-podcast-state     {currentEpisode, playbackRate}
 */
(() => {
  "use strict";

  const PROGRESS_KEY = "id-podcast-progress";
  const STATE_KEY    = "id-podcast-state";
  const COMPLETED_RATIO = 0.95;
  const FOLLOW_RESUME_MS = 4000;

  const fmtTime = (sec) => {
    if (!isFinite(sec) || sec < 0) sec = 0;
    sec = Math.floor(sec);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const loadProgress = () => {
    try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) || "{}"); }
    catch { return {}; }
  };
  const saveProgressMap = (m) => {
    try { localStorage.setItem(PROGRESS_KEY, JSON.stringify(m)); } catch {}
  };
  const setProgress = (slug, currentTime, duration) => {
    const m = loadProgress();
    m[slug] = {
      currentTime,
      duration,
      completed: duration > 0 ? (currentTime / duration) >= COMPLETED_RATIO : false,
      lastPlayed: Date.now(),
    };
    saveProgressMap(m);
  };

  const loadState = () => {
    try { return JSON.parse(localStorage.getItem(STATE_KEY) || "{}"); }
    catch { return {}; }
  };
  const saveState = (patch) => {
    try { localStorage.setItem(STATE_KEY, JSON.stringify({ ...loadState(), ...patch })); } catch {}
  };

  // --- Page identification ---
  const filename = (location.pathname.split("/").pop() || "index.html").toLowerCase();
  const isListenPage = filename === "listen.html";
  const currentSlug = filename.replace(/\.html$/, "");
  const isChapterPage = /^\d{2}-/.test(currentSlug);

  // --- Async manifest loaders, with in-tab cache ---
  let _masterPromise = null;
  const loadMaster = () => {
    if (_masterPromise) return _masterPromise;
    _masterPromise = fetch("assets/podcast/audio_manifest.json", { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : []))
      .catch(() => []);
    return _masterPromise;
  };
  const loadEpisode = (slug) =>
    fetch(`assets/podcast/${slug}.json`, { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null);

  // ====================================================================
  //   MINI-PLAYER (chapter pages)
  // ====================================================================
  async function setupMiniPlayer() {
    const mount = document.getElementById("mini-player");
    if (!mount) return;
    const slug = mount.dataset.slug || currentSlug;
    const master = await loadMaster();
    const ep = master.find((e) => e.id === slug);
    if (!ep) {
      mount.remove();
      return;
    }

    // Inline CTA in the article (above mini-player) — full-width call-out
    insertChapterAudioCta(ep);

    // Bottom bar
    document.body.classList.add("has-mini-player");
    mount.removeAttribute("hidden");
    mount.classList.add("mp");
    mount.innerHTML = `
      <div class="mp__cover" style="background-image:url('assets/podcast/${ep.cover}')"></div>
      <div class="mp__main">
        <div class="mp__title">${escapeHtml(ep.title)}</div>
        <div class="mp__row">
          <span class="mp__time mp__time-cur">0:00</span>
          <div class="mp__bar" role="progressbar" aria-label="Audio progress"><div class="mp__fill"></div></div>
          <span class="mp__time mp__time-tot">${fmtTime(ep.duration)}</span>
        </div>
      </div>
      <div class="mp__actions">
        <button class="mp__btn mp__btn-play" type="button" aria-label="Play">▶</button>
        <a class="mp__open" href="listen.html?ep=${encodeURIComponent(slug)}">Player view →</a>
      </div>
    `;

    const audio = new Audio();
    audio.preload = "metadata";
    pickSource(audio, ep);

    const btn  = mount.querySelector(".mp__btn-play");
    const fill = mount.querySelector(".mp__fill");
    const bar  = mount.querySelector(".mp__bar");
    const tcur = mount.querySelector(".mp__time-cur");
    const tcta = mount.querySelector(".mp__time-tot");
    const open = mount.querySelector(".mp__open");

    // Resume from saved progress
    const saved = loadProgress()[slug];
    if (saved && saved.currentTime && saved.currentTime < (ep.duration - 5)) {
      audio.currentTime = saved.currentTime;
      const ratio = saved.currentTime / ep.duration;
      fill.style.width = `${ratio * 100}%`;
      tcur.textContent = fmtTime(saved.currentTime);
    }

    btn.addEventListener("click", () => {
      if (audio.paused) audio.play().catch(() => {});
      else audio.pause();
    });
    audio.addEventListener("play",  () => (btn.textContent = "❚❚"));
    audio.addEventListener("pause", () => (btn.textContent = "▶"));
    audio.addEventListener("ended", () => (btn.textContent = "▶"));

    audio.addEventListener("loadedmetadata", () => {
      if (isFinite(audio.duration)) tcta.textContent = fmtTime(audio.duration);
    });
    audio.addEventListener("timeupdate", () => {
      const dur = audio.duration || ep.duration;
      const ratio = dur > 0 ? audio.currentTime / dur : 0;
      fill.style.width = `${(ratio * 100).toFixed(2)}%`;
      tcur.textContent = fmtTime(audio.currentTime);
      // throttled save — every ~3s
      if (Math.floor(audio.currentTime) % 3 === 0) setProgress(slug, audio.currentTime, dur);
    });
    bar.addEventListener("click", (e) => {
      const rect = bar.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      const dur = audio.duration || ep.duration;
      audio.currentTime = Math.max(0, Math.min(dur - 0.1, dur * ratio));
    });
    open.addEventListener("click", () => {
      // forward current playback position so listen.html can pick up where we are
      if (audio.currentTime > 0) {
        open.href = `listen.html?ep=${encodeURIComponent(slug)}&t=${audio.currentTime.toFixed(1)}`;
      }
    });
  }

  function insertChapterAudioCta(ep) {
    const article = document.querySelector("main.content article");
    if (!article) return;
    if (article.querySelector(".audio-cta")) return;
    const cta = document.createElement("div");
    cta.className = "audio-cta";
    cta.innerHTML = `
      <div>
        <div class="audio-cta__label">Listen to this chapter</div>
        <div class="audio-cta__title">${escapeHtml(ep.title)}</div>
        <div class="audio-cta__meta">${fmtTime(ep.duration)} · two hosts</div>
      </div>
      <a class="audio-cta__cta" href="listen.html?ep=${encodeURIComponent(ep.id)}">Open player ▸</a>
    `;
    // Insert after the H1 / first heading, falling back to top of article
    const firstH1 = article.querySelector("h1, h2");
    if (firstH1 && firstH1.nextSibling) firstH1.parentNode.insertBefore(cta, firstH1.nextSibling);
    else article.insertBefore(cta, article.firstChild);
  }

  // ====================================================================
  //   LISTEN PAGE (full player + transcript + playlist)
  // ====================================================================
  async function setupListenPage() {
    document.body.classList.add("listen-page");

    const params = new URLSearchParams(location.search);
    let slug = params.get("ep");
    const seekT = parseFloat(params.get("t") || "0");

    const master = await loadMaster();
    if (!master.length) {
      renderListenEmpty("No episodes yet. Generate audio with docs/build_audio.py and refresh.");
      return;
    }

    // Default: last played, else first
    if (!slug) {
      const state = loadState();
      slug = state.currentEpisode && master.find((e) => e.id === state.currentEpisode)
        ? state.currentEpisode
        : master[0].id;
    }
    const meta = master.find((e) => e.id === slug);
    if (!meta) {
      renderListenEmpty(`Episode "${slug}" not found.`);
      return;
    }

    saveState({ currentEpisode: slug });

    const ep = await loadEpisode(slug);
    if (!ep) {
      renderListenEmpty(`Could not load transcript for "${slug}".`);
      return;
    }

    renderListen(ep, master, seekT);
  }

  function renderListenEmpty(msg) {
    const main = document.querySelector("main.content");
    if (!main) return;
    main.innerHTML = `
      <div class="listen">
        <div class="listen__main">
          <div class="listen__empty">${escapeHtml(msg)}</div>
        </div>
      </div>
    `;
  }

  function renderListen(ep, master, seekT) {
    const main = document.querySelector("main.content");
    if (!main) return;

    const state = loadState();
    const rate  = state.playbackRate || 1.0;

    main.innerHTML = `
      <div class="listen">
        <div class="listen__main">
          <div class="np-card">
            <div class="np-card__cover" style="background-image:url('assets/podcast/${ep.cover}')"></div>
            <div>
              <div class="np-card__section">${escapeHtml(ep.section)}</div>
              <h1 class="np-card__title">${escapeHtml(ep.title)}</h1>
              <div class="np-card__meta">${fmtTime(ep.duration)} · ${ep.turns.length} turns · ${ep.voices.host_a} + ${ep.voices.host_b}</div>
            </div>
          </div>

          <div class="transport">
            <div class="transport__head" aria-hidden="true">
              <div class="transport__thumb" style="background-image:url('assets/podcast/${ep.cover}')"></div>
              <div class="transport__heads">
                <div class="transport__head-section">${escapeHtml(ep.section)}</div>
                <div class="transport__head-title">${escapeHtml(ep.title)}</div>
              </div>
            </div>
            <div class="transport__row">
              <button class="transport__btn transport__btn--skip" data-skip="-15" aria-label="Back 15s">⟲15</button>
              <button class="transport__btn transport__btn--play" aria-label="Play">▶</button>
              <button class="transport__btn transport__btn--skip" data-skip="15" aria-label="Forward 15s">15⟳</button>
              <span class="transport__time">0:00 / ${fmtTime(ep.duration)}</span>
              <input class="transport__scrub" type="range" min="0" max="${ep.duration}" step="0.1" value="0" aria-label="Seek">
              <select class="transport__rate" aria-label="Playback speed">
                <option value="0.75">0.75×</option>
                <option value="1" selected>1×</option>
                <option value="1.25">1.25×</option>
                <option value="1.5">1.5×</option>
                <option value="2">2×</option>
              </select>
            </div>
          </div>

          <div class="transcript"></div>
        </div>

        <aside class="listen__playlist">
          <div class="pl__heading">All episodes</div>
          ${renderPlaylist(master, ep.id)}
        </aside>
      </div>
    `;

    // Audio element (kept off-DOM)
    const audio = new Audio();
    audio.preload = "metadata";
    audio.playbackRate = rate;
    pickSource(audio, ep);

    // Document title
    document.title = `${ep.title} — Indian Democracy: Audio`;

    // Transcript turns
    const transcript = main.querySelector(".transcript");
    const speakerLabel = (k) => (k === "host_a" ? "Neha" : "Aditya");
    transcript.innerHTML = ep.turns
      .map((t, i) => `
        <p class="transcript__turn" data-i="${i}" data-start="${t.start}" data-end="${t.end}">
          <span class="transcript__speaker">${speakerLabel(t.speaker)}</span>${escapeHtml(t.text)}
        </p>`)
      .join("");
    const turnEls = Array.from(transcript.querySelectorAll(".transcript__turn"));

    // Controls
    const playBtn = main.querySelector(".transport__btn--play");
    const scrub   = main.querySelector(".transport__scrub");
    const timeEl  = main.querySelector(".transport__time");
    const rateSel = main.querySelector(".transport__rate");
    rateSel.value = String(rate);

    main.querySelectorAll(".transport__btn--skip").forEach((b) => {
      b.addEventListener("click", () => {
        audio.currentTime = Math.max(0, Math.min(audio.duration - 0.1, audio.currentTime + Number(b.dataset.skip)));
      });
    });
    playBtn.addEventListener("click", () => {
      if (audio.paused) audio.play().catch(() => {});
      else audio.pause();
    });
    audio.addEventListener("play",  () => { playBtn.textContent = "❚❚"; setMediaPlaying(true); });
    audio.addEventListener("pause", () => { playBtn.textContent = "▶";  setMediaPlaying(false); });
    audio.addEventListener("ended", () => { playBtn.textContent = "▶"; });

    scrub.addEventListener("input", () => { audio.currentTime = Number(scrub.value); });
    rateSel.addEventListener("change", () => {
      audio.playbackRate = Number(rateSel.value);
      saveState({ playbackRate: audio.playbackRate });
    });

    // Click-to-seek on transcript turn
    turnEls.forEach((el) => {
      el.addEventListener("click", () => {
        audio.currentTime = Number(el.dataset.start);
        if (audio.paused) audio.play().catch(() => {});
      });
    });

    // Per-turn highlight loop (binary search via rAF)
    let currentIdx = -1;
    let lastProgrammaticScrollTop = 0;
    let autoFollow = true;
    let resumeFollowTimer = null;
    let followPillEl = null;

    const findCurrentTurn = (t) => {
      let lo = 0, hi = ep.turns.length - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const turn = ep.turns[mid];
        if (t < turn.start) hi = mid - 1;
        else if (t >= turn.end) lo = mid + 1;
        else return mid;
      }
      return Math.max(0, Math.min(hi, ep.turns.length - 1));
    };

    const onTimeUpdate = () => {
      const t = audio.currentTime;
      const dur = audio.duration || ep.duration;
      timeEl.textContent = `${fmtTime(t)} / ${fmtTime(dur)}`;
      scrub.value = t;

      const idx = findCurrentTurn(t);
      if (idx !== currentIdx) {
        if (currentIdx >= 0 && turnEls[currentIdx]) {
          turnEls[currentIdx].classList.remove("transcript__turn--current");
          turnEls[currentIdx].classList.add("transcript__turn--past");
          turnEls[currentIdx].removeAttribute("aria-current");
        }
        if (turnEls[idx]) {
          turnEls[idx].classList.add("transcript__turn--current");
          turnEls[idx].classList.remove("transcript__turn--past");
          turnEls[idx].setAttribute("aria-current", "true");
          // Also clear past from any later turn that may have been marked
          // (happens if user scrubs backward)
          for (let j = idx + 1; j < turnEls.length; j++) {
            turnEls[j].classList.remove("transcript__turn--past");
          }
          if (autoFollow) scrollTurnIntoView(turnEls[idx]);
        }
        currentIdx = idx;
      }
      if (Math.floor(t) % 3 === 0) setProgress(ep.id, t, dur);
    };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("loadedmetadata", () => {
      // Resume from URL ?t= or saved progress
      const saved = loadProgress()[ep.id];
      const target = seekT > 0
        ? seekT
        : (saved && saved.currentTime && saved.currentTime < audio.duration - 5 ? saved.currentTime : 0);
      if (target > 0) audio.currentTime = target;
    });

    function scrollTurnIntoView(el) {
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const wantTop = rect.top + window.scrollY - (vh / 2) + (rect.height / 2);
      lastProgrammaticScrollTop = wantTop;
      window.scrollTo({ top: wantTop, behavior: "smooth" });
    }

    // Manual-scroll detection
    let scrollT = null;
    window.addEventListener("scroll", () => {
      if (Math.abs(window.scrollY - lastProgrammaticScrollTop) < 40) return;
      if (!autoFollow) return;
      autoFollow = false;
      showFollowPill();
      if (resumeFollowTimer) clearTimeout(resumeFollowTimer);
      resumeFollowTimer = setTimeout(() => {
        autoFollow = true;
        hideFollowPill();
      }, FOLLOW_RESUME_MS);
      // Each scroll bumps the timer
      window.addEventListener("scroll", bumpResumeTimer, { passive: true, once: false });
    }, { passive: true });
    function bumpResumeTimer() {
      if (!autoFollow && resumeFollowTimer) {
        clearTimeout(resumeFollowTimer);
        resumeFollowTimer = setTimeout(() => {
          autoFollow = true;
          hideFollowPill();
        }, FOLLOW_RESUME_MS);
      }
    }
    function showFollowPill() {
      if (followPillEl) return;
      followPillEl = document.createElement("button");
      followPillEl.className = "follow-pill";
      followPillEl.type = "button";
      followPillEl.innerHTML = "↓ Resume follow";
      followPillEl.addEventListener("click", () => {
        autoFollow = true;
        if (currentIdx >= 0 && turnEls[currentIdx]) scrollTurnIntoView(turnEls[currentIdx]);
        hideFollowPill();
      });
      document.body.appendChild(followPillEl);
      requestAnimationFrame(() => followPillEl.classList.add("show"));
    }
    function hideFollowPill() {
      if (!followPillEl) return;
      followPillEl.classList.remove("show");
      const el = followPillEl;
      followPillEl = null;
      setTimeout(() => el.remove(), 220);
    }

    // Media Session API
    if ("mediaSession" in navigator) {
      const coverUrl = new URL(`assets/podcast/${ep.cover}`, location.href).href;
      navigator.mediaSession.metadata = new MediaMetadata({
        title:  ep.title,
        artist: "Indian Democracy Guide",
        album:  ep.section,
        artwork: [
          { src: coverUrl, sizes: "1024x1024", type: "image/png" },
        ],
      });
      navigator.mediaSession.setActionHandler("play",  () => audio.play().catch(() => {}));
      navigator.mediaSession.setActionHandler("pause", () => audio.pause());
      navigator.mediaSession.setActionHandler("seekbackward", () => { audio.currentTime = Math.max(0, audio.currentTime - 15); });
      navigator.mediaSession.setActionHandler("seekforward",  () => { audio.currentTime = Math.min(audio.duration - 0.1, audio.currentTime + 15); });
      try {
        navigator.mediaSession.setActionHandler("seekto", (d) => { if (d.seekTime != null) audio.currentTime = d.seekTime; });
      } catch {}
      // Previous / next episode
      const idx = master.findIndex((e) => e.id === ep.id);
      if (idx > 0) navigator.mediaSession.setActionHandler("previoustrack", () => {
        location.search = `?ep=${encodeURIComponent(master[idx - 1].id)}`;
      });
      if (idx < master.length - 1) navigator.mediaSession.setActionHandler("nexttrack", () => {
        location.search = `?ep=${encodeURIComponent(master[idx + 1].id)}`;
      });
    }

    function setMediaPlaying(playing) {
      if ("mediaSession" in navigator) {
        navigator.mediaSession.playbackState = playing ? "playing" : "paused";
      }
    }

    // Auto-play if URL had ?t= (user clicked from mini-player mid-listen)
    if (seekT > 0) {
      const tryAutoplay = () => audio.play().catch(() => {});
      audio.addEventListener("canplay", tryAutoplay, { once: true });
    }

    // Compact-on-scroll: when the big now-playing card scrolls out of view,
    // reveal the sticky transport's mini "now playing" header.
    const npCard = main.querySelector(".np-card");
    const transport = main.querySelector(".transport");
    if (npCard && transport && "IntersectionObserver" in window) {
      const io = new IntersectionObserver(
        ([entry]) => {
          transport.classList.toggle("transport--compact", !entry.isIntersecting);
        },
        { threshold: 0, rootMargin: "-80px 0px 0px 0px" }
      );
      io.observe(npCard);
    }
  }

  function renderPlaylist(master, currentId) {
    // Group by section, preserving master-manifest order
    const groups = [];
    const seen = new Map();
    for (const e of master) {
      let g = seen.get(e.section);
      if (!g) { g = { section: e.section, items: [] }; seen.set(e.section, g); groups.push(g); }
      g.items.push(e);
    }
    const prog = loadProgress();
    return groups.map((g) => `
      <div class="pl__section">${escapeHtml(g.section)}</div>
      <ol class="pl__list">
        ${g.items.map((e, i) => {
          const num = e.id.split("-")[0];
          const cls = ["pl__item"];
          if (e.id === currentId) cls.push("pl__item--current");
          const completed = prog[e.id]?.completed ? " ✓" : "";
          return `
            <li>
              <a class="${cls.join(' ')}" href="?ep=${encodeURIComponent(e.id)}">
                <span class="pl__num">${num}</span>
                <span class="pl__title">${escapeHtml(e.title)}${completed}</span>
                <span class="pl__dur">${fmtTime(e.duration)}</span>
              </a>
            </li>`;
        }).join("")}
      </ol>
    `).join("");
  }

  // --- Helpers ---
  function pickSource(audio, ep) {
    // MP3 is universal and known to play correctly across all current browsers.
    // (We still encode WebM/Opus for future use / RSS variety, but skip it here
    // because some browsers report support but then play it silently.)
    audio.src = `assets/podcast/${ep.audio.mp3}`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // --- Service worker registration (best effort, no failure if SW missing) ---
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("service-worker.js").catch(() => {});
    });
  }

  // --- Boot ---
  if (isListenPage) setupListenPage();
  else if (isChapterPage) setupMiniPlayer();
})();
