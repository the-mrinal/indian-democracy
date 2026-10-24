#!/usr/bin/env python3
"""
build_site.py — Generate the Indian Democracy HTML site from the markdown chapters.

Reads docs/markdown/NN-slug.md, converts to HTML, wraps in the shared layout
(sidebar navigation + chapter chrome) and writes to docs/site/NN-slug.html.

Run:  python3 docs/build_site.py
"""
from __future__ import annotations
import json
import re
import sys
from email.utils import formatdate
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Install the markdown library:  python3 -m pip install --user markdown")

# Override at the command-line via env var if you're deploying elsewhere
SITE_URL = "https://mrinalchandra.github.io/indian-democracy"

ROOT = Path(__file__).resolve().parent
MD_DIR = ROOT / "markdown"
SITE_DIR = ROOT / "site"

# ---------- Canonical chapter list (slug, sidebar title, sidebar group) ----------
CHAPTERS: list[tuple[str, str, str]] = [
    ("01-introduction",          "Introduction: India as a Democracy",            "Foundations"),
    ("02-constitution",          "The Constitution: Birth, Structure, Soul",      "Foundations"),
    ("03-rights-duties-dpsp",    "Rights, Duties & Directive Principles",         "Foundations"),
    ("04-federalism",            "Federalism: Union, States, UTs",                "Foundations"),
    ("05-union-executive",       "Union Executive: President, VP, PM, Cabinet",   "Union Government"),
    ("06-lok-sabha",             "Lok Sabha — The House of the People",           "Union Government"),
    ("07-rajya-sabha",           "Rajya Sabha — The Council of States",           "Union Government"),
    ("08-how-bill-becomes-law",  "How a Bill Becomes Law",                        "Union Government"),
    ("09-state-government",      "State Government: Governor, CM, MLAs",          "State Government"),
    ("10-judiciary",             "The Judiciary: Supreme Court & High Courts",    "Other Pillars"),
    ("11-eci-and-bodies",        "Election Commission & Constitutional Bodies",   "Other Pillars"),
    ("12-how-elections-work",    "How an Indian Election Actually Runs",          "Elections"),
    ("13-electoral-math",        "Electoral Systems: FPTP, STV & the Math",       "Elections"),
    ("14-local-government",      "Local Self-Government: Panchayats & Nagar Palikas", "Local Government"),
    ("15-parties-and-defection", "Political Parties & the Anti-Defection Law",    "Politics in Practice"),
    ("16-money-in-politics",     "Money in Politics: Finance, Bonds, Criminalisation", "Politics in Practice"),
    ("17-ground-execution",      "Ground-Level Campaign Execution",               "Politics in Practice"),
    ("18-recent-elections",      "Recent Elections: 2024 LS → 2026 State Cycle",  "Today"),
    ("19-glossary-references",   "Glossary, Timeline & References",               "Reference"),
]

INDEX_SLUG = "index"

# ---------- HTML layout ----------
LAYOUT = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title} — Indian Democracy: A Complete Guide</title>
  <meta name="description" content="{description}">
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="podcast.css">
  <link rel="manifest" href="manifest.json">
  <meta name="theme-color" content="#000080">
  <link rel="apple-touch-icon" sizes="192x192" href="assets/icons/192.png">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <a class="brand" href="index.html">
        <span class="brand-flag" aria-hidden="true"></span>
        <span>
          <span class="brand-title">Indian Democracy</span><br>
          <span class="brand-sub">A complete study guide</span>
        </span>
      </a>
{sidebar}
      <div class="sidebar-foot">
        Built {built_date} · Sources cited per chapter.<br>
        Anchored in M. Laxmikanth's <em>Indian Polity</em> and Shivam Shankar Singh's <em>How to Win an Indian Election</em>.
      </div>
    </aside>
    <main class="content">
      <article>
{body}
{pager}
      </article>
    </main>
  </div>
  <div id="mini-player" hidden></div>
  <script src="bookmarks.js" defer></script>
  <script src="podcast.js" defer></script>
</body>
</html>
"""

PAGER_HTML = """
        <nav class="pager">
          {prev}
          {next}
        </nav>"""

def build_sidebar(active_slug: str) -> str:
    """Build the sidebar nav, grouped by section, with `active` class on current page."""
    parts: list[str] = []
    current_group: str | None = None
    for slug, title, group in CHAPTERS:
        if group != current_group:
            if current_group is not None:
                parts.append("      </ol>")
            parts.append(f'      <div class="nav-section">{group}</div>')
            parts.append("      <ol>")
            current_group = group
        active = " active" if slug == active_slug else ""
        parts.append(f'        <li><a class="ch{active}" href="{slug}.html">{title}</a></li>')
    parts.append("      </ol>")
    return "\n".join(parts)

def build_pager(idx: int) -> str:
    prev_link = ""
    next_link = ""
    if idx > 0:
        slug, title, _ = CHAPTERS[idx - 1]
        prev_link = (
            f'<a href="{slug}.html"><span class="label">← Previous</span>'
            f'<strong>{title}</strong></a>'
        )
    else:
        prev_link = '<span></span>'
    if idx < len(CHAPTERS) - 1:
        slug, title, _ = CHAPTERS[idx + 1]
        next_link = (
            f'<a href="{slug}.html" style="text-align:right;">'
            f'<span class="label">Next →</span><strong>{title}</strong></a>'
        )
    else:
        next_link = '<span></span>'
    return PAGER_HTML.format(prev=prev_link, next=next_link)

def md_to_html(text: str) -> str:
    """Convert markdown body to HTML, then post-process tables to wrap in scroll containers."""
    html = markdown.markdown(
        text,
        extensions=["extra", "tables", "sane_lists", "toc", "attr_list"],
        output_format="html5",
    )
    # Wrap each <table> in a div.table-wrap for horizontal scroll on mobile.
    html = re.sub(r"(<table\b)", r'<div class="table-wrap">\1', html)
    html = re.sub(r"(</table>)", r"\1</div>", html)
    return html

def render_chapter(idx: int, slug: str, title: str) -> None:
    md_path = MD_DIR / f"{slug}.md"
    if not md_path.exists():
        print(f"  [skip] {md_path.name} not found (chapter not yet written)")
        return
    raw = md_path.read_text(encoding="utf-8")
    # Strip leading H1 if present so we can use it as title and not double-render
    body_md = re.sub(r"^# .+\n+", "", raw, count=1)
    body_html = md_to_html(body_md)
    description = first_paragraph(body_md).replace("\n", " ")[:170]
    page = LAYOUT.format(
        title=title,
        description=description,
        sidebar=build_sidebar(slug),
        body=body_html,
        pager=build_pager(idx),
        built_date="June 2026",
    )
    out = SITE_DIR / f"{slug}.html"
    out.write_text(page, encoding="utf-8")
    print(f"  [ok]   {slug}.html ({len(page):,} bytes)")

def first_paragraph(md: str) -> str:
    for block in md.split("\n\n"):
        block = block.strip()
        if block and not block.startswith(("#", "<", "-", "*", "|", ">", "1.")):
            return block
    return ""

def render_index() -> None:
    md_path = MD_DIR / "index.md"
    if not md_path.exists():
        print("  [skip] index.md not found")
        return
    raw = md_path.read_text(encoding="utf-8")
    body_md = re.sub(r"^# .+\n+", "", raw, count=1)
    body_html = md_to_html(body_md)
    page = LAYOUT.format(
        title="Home",
        description="A complete, citation-backed guide to India's democracy, government, and elections.",
        sidebar=build_sidebar("__index__"),  # nothing active
        body=body_html,
        pager="",
        built_date="June 2026",
    )
    out = SITE_DIR / "index.html"
    out.write_text(page, encoding="utf-8")
    print(f"  [ok]   index.html ({len(page):,} bytes)")

# ====================================================================
# Podcast site-integration renderers
# ====================================================================

def _escape_xml(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def render_audio_manifest() -> list[dict]:
    """Walk per-episode JSONs under site/assets/podcast/ → master audio_manifest.json."""
    podcast_dir = SITE_DIR / "assets" / "podcast"
    podcast_dir.mkdir(parents=True, exist_ok=True)
    eps: list[dict] = []
    for slug, _title, _group in CHAPTERS:
        p = podcast_dir / f"{slug}.json"
        if not p.exists():
            continue
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
            eps.append({k: meta[k] for k in ("id", "title", "section", "kind", "duration", "audio", "cover")})
        except Exception as e:
            print(f"  [warn] could not parse {p.name}: {e}")
    out = podcast_dir / "audio_manifest.json"
    out.write_text(json.dumps(eps, indent=2), encoding="utf-8")
    print(f"  [ok]   audio_manifest.json ({len(eps)} episodes)")
    return eps


def render_listen_page() -> None:
    page = LAYOUT.format(
        title="Listen — Audio Companion",
        description="Audio companion to the Indian Democracy guide. Two-host conversations per chapter.",
        sidebar=build_sidebar("__listen__"),
        body='<div id="listen-root"></div>',
        pager="",
        built_date="June 2026",
    )
    (SITE_DIR / "listen.html").write_text(page, encoding="utf-8")
    print(f"  [ok]   listen.html")


def render_pwa_manifest() -> None:
    manifest = {
        "name": "Indian Democracy: A Complete Guide",
        "short_name": "Indian Democracy",
        "description": "A complete study guide to India's democracy, government, and elections — with an audio companion.",
        "start_url": "index.html",
        "scope": "./",
        "display": "standalone",
        "orientation": "portrait",
        "theme_color": "#000080",
        "background_color": "#fdfdfb",
        "icons": [
            {"src": "assets/icons/192.png",  "sizes": "192x192",   "type": "image/png", "purpose": "any maskable"},
            {"src": "assets/icons/512.png",  "sizes": "512x512",   "type": "image/png", "purpose": "any maskable"},
            {"src": "assets/icons/1024.png", "sizes": "1024x1024", "type": "image/png"},
        ],
    }
    (SITE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  [ok]   manifest.json")


def render_service_worker() -> None:
    precache: list[str] = [
        "index.html", "listen.html",
        "styles.css", "podcast.css",
        "bookmarks.js", "podcast.js",
        "manifest.json",
        "assets/icons/192.png", "assets/icons/512.png", "assets/icons/1024.png",
    ]
    for slug, _t, _g in CHAPTERS:
        precache.append(f"{slug}.html")
    sw = f"""// Auto-generated by build_site.py
const CACHE = "id-shell-v2";
const PRECACHE = {json.dumps(precache)};

self.addEventListener("install", (e) => {{
  e.waitUntil(
    caches.open(CACHE).then((c) => Promise.all(
      PRECACHE.map((u) => c.add(u).catch(() => null))
    ))
  );
  self.skipWaiting();
}});

self.addEventListener("activate", (e) => {{
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
}});

self.addEventListener("fetch", (e) => {{
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  // Don't intercept audio (large) or podcast JSON (volatile)
  if (url.pathname.endsWith(".mp3") || url.pathname.endsWith(".webm")) return;
  if (url.pathname.includes("/podcast/") && url.pathname.endsWith(".json")) return;
  e.respondWith(
    caches.match(req).then((cached) => {{
      const fetchAndUpdate = fetch(req).then((resp) => {{
        if (resp && resp.ok) {{
          const clone = resp.clone();
          caches.open(CACHE).then((c) => c.put(req, clone)).catch(() => {{}});
        }}
        return resp;
      }}).catch(() => cached);
      return cached || fetchAndUpdate;
    }})
  );
}});
"""
    (SITE_DIR / "service-worker.js").write_text(sw, encoding="utf-8")
    print(f"  [ok]   service-worker.js ({len(precache)} precache entries)")


def render_feed(episodes: list[dict]) -> None:
    """RSS 2.0 + iTunes namespace, Apple Podcasts / Overcast compatible."""
    now_rfc = formatdate(usegmt=True)
    items: list[str] = []
    for ep in episodes:
        items.append(
            "    <item>\n"
            f"      <title>{_escape_xml(ep['title'])}</title>\n"
            f"      <description>{_escape_xml(ep.get('section', ''))}</description>\n"
            f"      <enclosure url=\"{SITE_URL}/assets/podcast/{ep['audio']['mp3']}\" type=\"audio/mpeg\" length=\"0\"/>\n"
            f"      <guid isPermaLink=\"false\">{ep['id']}</guid>\n"
            f"      <pubDate>{now_rfc}</pubDate>\n"
            f"      <itunes:image href=\"{SITE_URL}/assets/podcast/{ep['cover']}\"/>\n"
            f"      <itunes:duration>{int(round(ep['duration']))}</itunes:duration>\n"
            "    </item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
        "  <channel>\n"
        "    <title>Indian Democracy: A Complete Guide</title>\n"
        f"    <link>{SITE_URL}/</link>\n"
        "    <description>Two-host conversational audio companion to a 19-chapter guide on India's democracy.</description>\n"
        "    <language>en-IN</language>\n"
        "    <itunes:author>Indian Democracy Guide</itunes:author>\n"
        f"    <itunes:image href=\"{SITE_URL}/assets/icons/1024.png\"/>\n"
        "    <itunes:explicit>false</itunes:explicit>\n"
        '    <itunes:category text="Government"/>\n'
        '    <itunes:category text="Education"/>\n'
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
    (SITE_DIR / "feed.xml").write_text(xml, encoding="utf-8")
    print(f"  [ok]   feed.xml ({len(episodes)} items)")


def render_app_icons() -> None:
    """Generate flag-themed PWA icons (192/512/1024). Idempotent."""
    icons_dir = SITE_DIR / "assets" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    sizes = (192, 512, 1024)
    if all((icons_dir / f"{s}.png").exists() for s in sizes):
        print(f"  [ok]   app icons (already present)")
        return
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print(f"  [skip] app icons (install Pillow: pip install Pillow)")
        return
    import math

    saffron = (255, 153, 51)
    green = (19, 136, 8)
    white = (253, 253, 251)
    navy = (0, 0, 128)

    for size in sizes:
        img = Image.new("RGB", (size, size), white)
        draw = ImageDraw.Draw(img)
        third = size // 3
        for y in range(size):
            if y < third:
                draw.line([(0, y), (size, y)], fill=saffron)
            elif y < 2 * third:
                draw.line([(0, y), (size, y)], fill=white)
            else:
                draw.line([(0, y), (size, y)], fill=green)
        r = size // 8
        cx = cy = size // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=navy, width=max(4, size // 100))
        spokes = 24
        for s in range(spokes):
            a = (s / spokes) * 2 * math.pi
            x1, y1 = cx + math.cos(a) * (r * 0.16), cy + math.sin(a) * (r * 0.16)
            x2, y2 = cx + math.cos(a) * (r * 0.95), cy + math.sin(a) * (r * 0.95)
            draw.line([(x1, y1), (x2, y2)], fill=navy, width=max(2, size // 220))
        img.save(icons_dir / f"{size}.png", "PNG", optimize=True)
    print(f"  [ok]   app icons (generated 192/512/1024)")


# ====================================================================
def main() -> None:
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Building site from {MD_DIR} → {SITE_DIR}")
    render_index()
    for i, (slug, title, _group) in enumerate(CHAPTERS):
        render_chapter(i, slug, title)

    print("\nPodcast integration:")
    render_app_icons()
    render_pwa_manifest()
    episodes = render_audio_manifest()
    render_listen_page()
    render_service_worker()
    if episodes:
        render_feed(episodes)
    else:
        print("  [skip] feed.xml (no episodes yet — re-run after build_audio.py)")
    print("\nDone.")

if __name__ == "__main__":
    main()
