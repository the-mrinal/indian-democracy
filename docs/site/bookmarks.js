/* Bookmark + reading-progress feature
 * Pure-client (localStorage). Run on every page via <script src="bookmarks.js" defer>.
 *
 * Behaviour
 * ---------
 * 1. Sidebar links get a green ✓ once a chapter is marked read.
 * 2. Each chapter page shows a progress strip at the top: "Chapter X of N · K% of guide read".
 * 3. A floating "Mark as read" pill bottom-right toggles the read state.
 * 4. Scrolling past 90% of a chapter auto-marks it as read.
 * 5. Scroll position is saved continuously; revisiting the same chapter offers
 *    a "Resume reading" toast to scroll back.
 * 6. The home page (index.html) shows a "Welcome back" card with the last-visited
 *    chapter and a Continue button, plus a Clear-bookmarks option.
 */
(() => {
  "use strict";

  const STORAGE_KEY_READ = "id-read-chapters";
  const STORAGE_KEY_LAST = "id-last-visited";
  const AUTO_READ_THRESHOLD = 0.9; // 90% scroll → mark as read

  // ---------- Storage helpers ----------
  const loadRead = () => new Set(JSON.parse(localStorage.getItem(STORAGE_KEY_READ) || "[]"));
  const saveRead = (s) => localStorage.setItem(STORAGE_KEY_READ, JSON.stringify([...s]));
  const loadLast = () => JSON.parse(localStorage.getItem(STORAGE_KEY_LAST) || "null");
  const saveLast = (slug, scrollY) =>
    localStorage.setItem(STORAGE_KEY_LAST, JSON.stringify({ slug, scrollY, ts: Date.now() }));

  let readChapters = loadRead();
  const lastVisited = loadLast();

  // ---------- Page identification ----------
  const sidebarLinks = Array.from(document.querySelectorAll(".sidebar ol li a.ch"));
  const allSlugs = sidebarLinks.map((a) => a.getAttribute("href").replace(/\.html$/, ""));
  const titleMap = Object.fromEntries(
    sidebarLinks.map((a) => [a.getAttribute("href").replace(/\.html$/, ""), a.textContent.trim()])
  );

  const filename = (window.location.pathname.split("/").pop() || "index.html").toLowerCase();
  const currentSlug = filename.replace(/\.html$/, "") || "index";
  const currentIndex = allSlugs.indexOf(currentSlug);
  const isChapterPage = currentIndex >= 0;

  // Save "I am here" on every page load (for chapter pages)
  if (isChapterPage) saveLast(currentSlug, 0);

  // ---------- Sidebar decoration ----------
  function decorateSidebar() {
    sidebarLinks.forEach((a) => {
      const slug = a.getAttribute("href").replace(/\.html$/, "");
      a.classList.toggle("read", readChapters.has(slug));
    });
  }
  decorateSidebar();

  // ---------- Progress strip on chapter pages ----------
  function buildProgressStrip() {
    if (!isChapterPage) return;
    const total = allSlugs.length;
    const readCount = allSlugs.filter((s) => readChapters.has(s)).length;
    const pct = Math.round((readCount / total) * 100);
    const strip = document.createElement("div");
    strip.className = "progress-strip";
    strip.innerHTML = `
      <div class="progress-meta">
        <strong>Chapter ${currentIndex + 1} of ${total}</strong>
        <span class="progress-text">${readCount} read · ${pct}% of guide</span>
      </div>
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
    `;
    const article = document.querySelector("main.content article");
    if (article) article.insertBefore(strip, article.firstChild);
  }
  buildProgressStrip();

  function refreshProgress() {
    if (!isChapterPage) return;
    const total = allSlugs.length;
    const readCount = allSlugs.filter((s) => readChapters.has(s)).length;
    const pct = Math.round((readCount / total) * 100);
    const fill = document.querySelector(".progress-fill");
    const text = document.querySelector(".progress-text");
    if (fill) fill.style.width = pct + "%";
    if (text) text.textContent = `${readCount} read · ${pct}% of guide`;
  }

  // ---------- Floating "Mark as read" pill ----------
  function buildBookmarkBtn() {
    if (!isChapterPage) return;
    const btn = document.createElement("button");
    btn.className = "bookmark-btn";
    btn.type = "button";
    btn.setAttribute("aria-label", "Toggle chapter as read");
    paintBtn(btn);
    btn.addEventListener("click", () => {
      if (readChapters.has(currentSlug)) readChapters.delete(currentSlug);
      else readChapters.add(currentSlug);
      saveRead(readChapters);
      paintBtn(btn);
      decorateSidebar();
      refreshProgress();
    });
    document.body.appendChild(btn);
  }
  function paintBtn(btn) {
    const isRead = readChapters.has(currentSlug);
    btn.classList.toggle("read", isRead);
    btn.innerHTML = isRead ? "✓ Marked as read" : "Mark as read";
  }
  buildBookmarkBtn();

  // ---------- Auto-mark on deep scroll + save scroll position ----------
  function setupScrollWatcher() {
    if (!isChapterPage) return;
    let ticking = false;
    const handler = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const ratio = docHeight > 0 ? scrollTop / docHeight : 0;
      saveLast(currentSlug, scrollTop);
      if (ratio >= AUTO_READ_THRESHOLD && !readChapters.has(currentSlug)) {
        readChapters.add(currentSlug);
        saveRead(readChapters);
        decorateSidebar();
        refreshProgress();
        const btn = document.querySelector(".bookmark-btn");
        if (btn) paintBtn(btn);
      }
    };
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          requestAnimationFrame(() => {
            handler();
            ticking = false;
          });
          ticking = true;
        }
      },
      { passive: true }
    );
  }
  setupScrollWatcher();

  // ---------- "Resume reading" toast (chapter pages) ----------
  function buildResumeToast() {
    if (!isChapterPage || !lastVisited) return;
    if (lastVisited.slug !== currentSlug) return;
    if (!lastVisited.scrollY || lastVisited.scrollY < 200) return;

    const toast = document.createElement("div");
    toast.className = "resume-hint";
    toast.innerHTML = `
      <span>You left off partway through this chapter.</span>
      <a href="#" class="rh-resume">↩ Resume from there</a>
      <button type="button" class="rh-close" aria-label="Dismiss">×</button>
    `;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    toast.querySelector(".rh-resume").addEventListener("click", (e) => {
      e.preventDefault();
      window.scrollTo({ top: lastVisited.scrollY, behavior: "smooth" });
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 250);
    });
    toast.querySelector(".rh-close").addEventListener("click", () => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 250);
    });
    // Auto-dismiss after 12 seconds
    setTimeout(() => {
      if (document.body.contains(toast)) {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 250);
      }
    }, 12000);
  }
  buildResumeToast();

  // ---------- "Welcome back" card on home page ----------
  function buildResumeCard() {
    if (currentSlug !== "index") return;
    if (!lastVisited || !lastVisited.slug) return;
    const title = titleMap[lastVisited.slug];
    if (!title) return;

    const total = allSlugs.length;
    const readCount = allSlugs.filter((s) => readChapters.has(s)).length;
    const pct = Math.round((readCount / total) * 100);

    const card = document.createElement("div");
    card.className = "resume-card";
    card.innerHTML = `
      <div class="rc-label">Welcome back</div>
      <div class="rc-title">Resume: ${title}</div>
      <div class="rc-meta">${readCount} of ${total} chapters read · ${pct}% of guide</div>
      <div class="rc-progress"><div class="rc-progress-fill" style="width:${pct}%"></div></div>
      <div class="rc-actions">
        <a class="rc-primary" href="${lastVisited.slug}.html">Continue reading →</a>
        <button type="button" class="rc-clear">Clear bookmarks</button>
      </div>
    `;

    // Insert after the lede
    const lede = document.querySelector(".lede");
    if (lede && lede.parentNode) {
      lede.parentNode.insertBefore(card, lede.nextSibling);
    } else {
      document.querySelector("article")?.insertBefore(card, document.querySelector("article").firstChild);
    }

    card.querySelector(".rc-clear").addEventListener("click", () => {
      if (confirm("Clear all reading bookmarks? This cannot be undone.")) {
        localStorage.removeItem(STORAGE_KEY_READ);
        localStorage.removeItem(STORAGE_KEY_LAST);
        location.reload();
      }
    });
  }
  buildResumeCard();
})();
